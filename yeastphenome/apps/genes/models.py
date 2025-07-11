from __future__ import unicode_literals

from django.apps import apps
from django.db import models
from django.db.models import F
from django.urls import reverse
from django.contrib.staticfiles.finders import find

import re
import faiss
import pandas as pd
import numpy as np

from scipy.stats import rankdata
from scipy.spatial.distance import cosine

from yeastphenome.apps.genes.managers import GeneManager, GeneAliasManager


class GeneAlias(models.Model):

    name = models.CharField(max_length=250, null=False, blank=False, unique=True)
    objects = GeneAliasManager()

    def __str__(self):
        return "%s" % self.name


class Gene(models.Model):

    # previously data.orf field, corresponds to 4. Feature name, YAL*
    systematic_name = models.CharField(
        max_length=50, null=True, blank=True, unique=True
    )

    # corresponds to 1. Primary SGDID, intended to query SGD API if needed
    # NOTE: unique removed from here and common name in the case of blank
    primary_sgdid = models.CharField(max_length=50, null=True, blank=True)

    # Corresponds to 5. Standard gene name, if defined
    common_name = models.CharField(max_length=50, null=True, blank=True)

    # Corresponds to 6. Alias (optional, multiples separated by |)
    aliases = models.ManyToManyField(GeneAlias, blank=True)

    common_name_explanation = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    puddu = models.CharField(max_length=50, null=True, blank=True)

    qc_comments = models.TextField(null=True, blank=True)

    objects = GeneManager()

    def __str__(self):
        return "%s / %s" % (self.common_name, self.systematic_name)

    def get_absolute_url(self):
        return reverse("genes:detail", args=(self.id,))

    def urlencode(self):
        # Remove all non-alphanumeric characters from the gene's common name
        common_name = re.sub(r'[^a-zA-Z0-9]', '', self.common_name)
        return "%s_%s" % (common_name, self.systematic_name)

    def aliases_list(self):
        return list(self.aliases.all().values_list("name", flat=True))

    def aliases_list_as_str(self):
        return "; ".join(self.aliases_list())

    def get_scores(self):
        datasets = apps.get_model("datasets", "Dataset").objects.all_valid()
        data = self.data.filter(dataset__in=datasets)
        data = data.filter(valuez__isnull=False)
        data = data.values("valuez", "dataset_id", dataset_name=F("dataset__name"))
        return data
    
    def get_similarities_faiss(self, n=None, ascending=False):
        
        file_path = find('genes/supcon_all_embeddings_geneid.txt')
        embeddings = pd.read_csv(file_path, sep='\t')
        num_genes = embeddings.shape[0]

        if n is None:
            n = num_genes
        
        object_ids = embeddings['id'].values
        systematic_names = embeddings['systematic_name'].values
        common_names = embeddings['common_name'].values

        embeddings.drop(columns=['id','systematic_name','common_name'], inplace=True)
        embeddings = np.ascontiguousarray(embeddings).astype(np.float32)

        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        faiss.normalize_L2(embeddings)
        index.add(embeddings.astype(np.float32))

        query_id = np.argwhere(object_ids == self.id)[0][0]
        query_embedding = embeddings[query_id]

        if ascending:
            distances, indices = index.search(-query_embedding.reshape(1, -1).astype(np.float32), k=n)
            distances = -distances
            ranks = rankdata(distances[0]) - 1
        else:
            distances, indices = index.search(query_embedding.reshape(1, -1).astype(np.float32), k=n)
            ranks = num_genes - (n - (rankdata(distances[0])-1))
            
        percentiles = 100 * ranks / (num_genes-1)
         
        scores = distances[0]
        gene2_ids = object_ids[indices[0]]
        gene2_common_names = common_names[indices[0]]
        gene2_systematic_names = systematic_names[indices[0]]

        data = []
        for i, gene2_id in enumerate(gene2_ids):
            data.append({
                'score': scores[i],
                'percentile': percentiles[i],
                'gene2_id': gene2_id,
                'gene2__systematic_name': gene2_systematic_names[i],
                'gene2__common_name': gene2_common_names[i]
            })

        return data
    
    def get_similarity_to_faiss(self, gene2):

        file_path = find('genes/supcon_all_embeddings_geneid.txt')
        embeddings = pd.read_csv(file_path, sep='\t', index_col=0)

        embeddings.drop(columns=['systematic_name','common_name'], inplace=True)

        embedding1 = embeddings.loc[self.id,:].values
        embedding2 = embeddings.loc[gene2.id,:].values

        cosine_sim = {'score': 1 - cosine(embedding1, embedding2)}

        return cosine_sim
