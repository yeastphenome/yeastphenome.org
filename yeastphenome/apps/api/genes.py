from django.conf import settings

from yeastphenome.apps.genes.models import Gene
from yeastphenome.apps.datasets.models import Data
from yeastphenome.apps.genes.search import run_search_tag_query as genes_search

from rest_framework.renderers import JSONRenderer
from ratelimit.mixins import RatelimitMixin

from rest_framework.response import Response
from rest_framework.views import APIView


class RunGenesQuery(RatelimitMixin, APIView):
    """server side render of genes explorer query"""

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request):
        print("GET RunGenesQuery")

        # Start and length to return
        start = int(request.GET["start"])
        length = int(request.GET["length"])
        draw = int(request.GET["draw"])
        query = request.GET["search[value]"]

        # Empty datatable
        data = {"draw": draw, "recordsTotal": 0, "recordsFiltered": 0, "data": []}
        queryset = []
        taglist = []
        count = 0

        order = request.GET["order[0][column]"]
        direction = request.GET["order[0][dir]"]  # asc or desc
        order_lookup = {
            "0asc": "common_name",
            "0desc": "-common_name",
            "1asc": "aliases__name",
            "1desc": "-aliases__name",
            "2asc": "primary_sgdid",
            "2desc": "-primary_sgdid",
        }

        for tag in request.GET.get("query", "").split("|"):
            if not tag:
                continue
            taglist.append(tag)

        # If we have an additional query, add to taglist
        if query:
            taglist.append(query)

        if taglist:
            queryset = genes_search(taglist)
            count = queryset.count()

        order_by = "%s%s" % (order, direction)
        if order_by in order_lookup and queryset:
            print(f"Ordering by {order_by}")
            queryset = queryset.order_by(order_lookup[order_by])

        if start > count:
            start = count - start
        end = start + length

        # If we've gone too far
        if end > count:
            end = count - 1

        if queryset:
            queryset = queryset[start : end + 1]

        data["recordsTotal"] = count
        data["recordsFiltered"] = count

        for gene in queryset:
            data["data"].append(
                [
                    gene.link_detail(),
                    ", ".join([alias.name for alias in gene.aliases.all()]),
                    gene.primary_sgdid,
                ]
            )
        return Response(status=200, data=data)


# Genes


class GetGeneDatasets(RatelimitMixin, APIView):
    """Given a gene serialize the datasets for a DataTable"""

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request, gene_id):
        print("GET GetGeneDatasets")

        # Start and length to return
        start = int(request.GET["start"])
        length = int(request.GET["length"])
        draw = int(request.GET["draw"])
        query = request.GET["search[value]"]

        # Empty datatable
        data = {"draw": draw, "recordsTotal": 0, "recordsFiltered": 0, "data": []}

        try:
            gene = Gene.objects.get(pk=gene_id)
        except Gene.DoesNotExist:
            return Response(status=200, data=data)

        order = request.GET["order[0][column]"]
        direction = request.GET["order[0][dir]"]  # asc or desc
        order_lookup = {
            "0asc": "dataset__name",
            "0desc": "-dataset__name",
            "1asc": "valuez",
            "1desc": "-valuez",
            "2asc": "valuez",
            "2desc": "-valuez",
        }

        datasets = (
            Data.objects.filter(gene=gene)
            .exclude(valuez__isnull=True)
            .order_by("-valuez")
        )

        # If there is a filter, we can currently filter based on dataset name
        if query:
            datasets = datasets.filter(dataset__name__icontains=query).distinct()

        order_by = "%s%s" % (order, direction)
        if order_by in order_lookup and datasets:
            print(f"Ordering by {order_by}")
            datasets = datasets.order_by(order_lookup[order_by])

        count = datasets.count()
        ranks = [(1 - (idx / count)) * 100 for idx, sim in enumerate(datasets)]
        if start > count:
            start = count - start
        end = start + length

        # Based on direction, reverse ranks
        if direction and "asc" in direction:
            ranks.reverse()

        # If we've gone too far
        if end > count:
            end = count - 1

        if datasets:
            datasets = datasets[start : end + 1]
            ranks = ranks[start : end + 1]

        data["recordsTotal"] = count
        data["recordsFiltered"] = count

        # Since we have a small queryset (25) we can loop over without it being too slow
        for i, dataset in enumerate(datasets):
            data["data"].append(
                [
                    "<a href='/datasets/%s/'>%s</a>"
                    % (dataset.dataset.id, dataset.dataset.name),
                    round(dataset.valuez, 1),
                    str(round(ranks[i], 1)) + "%",
                ]
            )

        # Must make model json serializable
        return Response(status=200, data=data)


class GetSimilarGenes(RatelimitMixin, APIView):
    """Given a gene's, return ordered list of similarity scores
    (most to least similar), top N for each
    """

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request, gene_id, N=10, reverse=0):
        print("GET GetSimilarGenes")
        try:
            gene = Gene.objects.get(pk=gene_id)
        except Gene.DoesNotExist:
            return Response(status=404)

        # A list of dicts
        scores = list(gene.get_ranked_similar(reverse=(reverse == 1)).values())
        data = {"scores": scores}

        # Must make model json serializable
        return Response(status=200, data=data)


class GetGenes(RatelimitMixin, APIView):
    """Return a list of all genes"""

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request):
        print("GET GetGenes")
        genes = list(Gene.objects.values_list("systematic_name", flat=True).distinct())
        return Response(status=200, data=genes)
