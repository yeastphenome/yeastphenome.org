from django.conf import settings
from django.contrib import messages

from yeastphenome.apps.datasets.models import Dataset, Collection, Gene, Data
from yeastphenome.apps.datasets.search import (
    run_search_tag_query as datasets_search,
    run_gene_search_tag_query as genes_search,
)

from rest_framework.renderers import JSONRenderer
from ratelimit.mixins import RatelimitMixin

from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q


# Helper Function to generate Dataset Cart buttons
def generate_datasets(request, data, datasets, query=None):
    """A shared view to take a request, and the started data, and generate
    the listing.
    """
    # Start and length to return
    start = int(request.GET["start"])
    length = int(request.GET["length"])
    query = request.GET["search[value]"]
    cart = request.session.get("cart", [])
    count = 0

    # If there is a filter
    if query and datasets:
        try:
            f = (
                Q(id=int(query))
                | Q(name__icontains=query)
                | Q(tags__name__icontains=query)
                | Q(collection__shortname__icontains=query)
                | Q(conditionset__display_name__icontains=query)
                | Q(paper__first_author__icontains=query)
                | Q(paper__last_author__icontains=query)
                | Q(phenotype__name__icontains=query)
                | Q(medium__display_name__icontains=query)
                | Q(phenotype__reporter__icontains=query)
                | Q(data_available__name__icontains=query)
            )
            datasets = datasets.filter(f).distinct()
        except:
            f = (
                Q(name__icontains=query)
                | Q(tags__name__icontains=query)
                | Q(collection__shortname__icontains=query)
                | Q(conditionset__display_name__icontains=query)
                | Q(paper__first_author__icontains=query)
                | Q(paper__last_author__icontains=query)
                | Q(phenotype__name__icontains=query)
                | Q(medium__display_name__icontains=query)
                | Q(phenotype__reporter__icontains=query)
                | Q(data_available__name__icontains=query)
            )
            datasets = datasets.filter(f).distinct()

    order = request.GET["order[0][column]"]
    direction = request.GET["order[0][dir]"]  # asc or desc
    order_lookup = {
        "0asc": "id",
        "0desc": "-id",
        "1asc": "paper__first_author",
        "1desc": "-paper__first_author",
        "2asc": "phenotype__name",
        "2desc": "-phenotype__name",
        "3asc": "conditionset__display_name",
        "3desc": "-conditionset__display_name",
        "4asc": "medium__display_name",
        "4desc": "-medium__display_name",
        "5asc": "collection__shortname",
        "5desc": "-collection__shortname",
        "6asc": "data_available",
        "6desc": "-data_available",
    }

    order_by = "%s%s" % (order, direction)
    if order_by in order_lookup and datasets:
        print(f"Ordering by {order_by}")

        # Some datasets don't have a conditionset, or medium will issue an error
        if order_by in ["3asc", "3desc"]:
            datasets = datasets.exclude(conditionset=None)
        elif order_by in ["4asc", "4desc"]:
            datasets = datasets.exclude(medium=None)
        elif order_by in ["5asc", "5desc"]:
            datasets = datasets.exclude(collection=None)
        datasets = datasets.order_by(order_lookup[order_by])

    if datasets:
        count = datasets.count()
        if start > count:
            start = count - start
        end = start + length

        # If we've gone too far
        if end > count:
            end = count - 1

        datasets = datasets[start : end + 1]

    data["recordsTotal"] = count
    data["recordsFiltered"] = count

    # Since we have a small queryset (25) we can loop over without it being too slow
    for dataset in datasets:

        if dataset.id not in cart:
            button = (
                '<button id="dataset-cart-%s" type="button" class="btn btn-primary btn-sm add-to-cart" style="width:120px" data-id="%s">Add</button>'
                % (dataset.id, dataset.id)
            )
        else:
            button = (
                '<button id="dataset-cart-%s" type="button" class="btn btn-danger btn-sm remove-from-cart" data-id="%s" style="width:120px">Remove</button>'
                % (dataset.id, dataset.id)
            )

        data["data"].append(
            [
                "<input id='%s' type='hidden' name='%s'><a id='%s' href='/datasets/%s'>%s</a>"
                % (dataset.id, dataset.id, dataset.id, dataset.id, dataset.id),
                str(dataset.paper),
                dataset.phenotype.name,
                getattr(dataset.conditionset, "display_name", ""),
                getattr(dataset.medium, "display_name", ""),
                getattr(dataset.collection, "shortname", ""),
                str(dataset.data_available or ""),
                button,
            ]
        )

    return data


class GetCartDatasets(RatelimitMixin, APIView):
    """Given a medium, serialize the datasets for a DataTable."""

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request):
        print("GET GetCartDatasets")

        # Start and length to return
        draw = int(request.GET["draw"])

        # Empty datatable
        data = {"draw": draw, "recordsTotal": 0, "recordsFiltered": 0, "data": []}
        cart = request.session.get("cart", [])
        datasets = Dataset.objects.filter(id__in=cart)
        data = generate_datasets(request, data, datasets)

        # Must make model json serializable
        return Response(status=200, data=data)


# Datasets Query


class RunDatasetsQuery(RatelimitMixin, APIView):
    """server side render of datasets explorer query"""

    ratelimit_key = "ip"
    ratelimit_rate = settings.VIEW_RATE_LIMIT
    ratelimit_block = settings.VIEW_RATE_LIMIT_BLOCK
    ratelimit_method = "GET"
    renderer_classes = (JSONRenderer,)

    def get(self, request, collection_id=None):
        print("GET RunDatasetsQuery")

        # Start and length to return
        draw = int(request.GET["draw"])

        # Empty datatable
        data = {"draw": draw, "recordsTotal": 0, "recordsFiltered": 0, "data": []}
        queryset = []
        taglist = []

        # The user can optionally be searching by a collection
        collection = None
        if collection_id:
            try:
                collection = Collection.objects.get(id=collection_id)
                messages.info(
                    request,
                    "Datasets shown are for collection %s (%s)"
                    % (collection.name, collection.shortname),
                )
            except Collection.DoesNotExist:
                messages.warning(
                    request, "We could not find collection with id %s" % collection_id
                )

        taglist = []
        for key in [
            "datatype",
            "tags",
            "medium",
            "conditions",
            "collection",
            "phenotype",
            "query",
        ]:
            for tag in request.GET.get(key, "").split("|"):
                if not tag:
                    continue
                taglist.append({"value": tag, "code": key})

        print(taglist)
        if taglist:
            queryset = datasets_search(
                query=None,
                taglist=taglist,
                return_instances=True,
                collection=collection,
            )

        data = generate_datasets(request, data, queryset)
        return Response(status=200, data=data)


# Genes Query


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

        for key in [
            "query",
        ]:
            for tag in request.GET.get(key, "").split("|"):
                if not tag:
                    continue
                taglist.append(tag)

        if taglist:
            queryset = genes_search(taglist)
            count = queryset.count()

        order_by = "%s%s" % (order, direction)
        if order_by in order_lookup and queryset:
            print(f"Ordering by {order_by}")
            queryset = queryset.order_by(order_lookup[order_by])

        # If there is a filter
        if query and queryset:
            f = (
                Q(systematic_name__iregex=query)
                | Q(common_name__iregex=query)
                | Q(primary_sgdid__iregex=query)
                | Q(aliases__name__iregex=query)
            )
            queryset = queryset.filter(f).distinct()
            count = queryset.count()

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

        datasets = (
            Data.objects.filter(gene=gene)
            .exclude(valuez__isnull=True)
            .order_by("-valuez")
        )

        # If there is a filter
        if query:
            f = Q(dataset__name__icontains=query)
            datasets = datasets.filter(f).distinct()

        count = datasets.count()
        ranks = [(1 - (idx / count)) * 100 for idx, sim in enumerate(datasets)]
        if start > count:
            start = count - start
        end = start + length

        # If we've gone too far
        if end > count:
            end = count - 1

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
                    round(ranks[i], 1),
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

        # # Only get top and bottom N
        # sims = list(gene.get_ranked_similar(reverse=(reverse == 1)))
        # first_n = sims[:N]
        # last_n = sims[len(sims) - N :]
        #
        # scores = {}
        # for sim in first_n + last_n:
        #     scores[sim.gene2.id] = {
        #         "gene2": sim.gene2,
        #         "score": sim.score,
        #         "pvalue": sim.pvalue
        #     }

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
