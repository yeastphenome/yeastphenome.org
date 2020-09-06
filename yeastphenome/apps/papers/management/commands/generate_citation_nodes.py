from django.core.management.base import BaseCommand
from django.db.models import Q

from yeastphenome.apps.papers.models import Paper
from yeastphenome.apps.papers.utils import get_paper_references

import json
import os

paperbase = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
root = os.path.dirname(os.path.dirname(paperbase))


class Command(BaseCommand):
    def handle(self, *args, **options):

        # This will generate a citation lookup that can be used to generate a citation graph proper
        nodes = {}
        papers = Paper.objects.filter(Q(latest_data_status__status__is_valid=True))

        # First generate nodes lookup, and listing of nodes
        count = 0
        for paper in papers:
            node = {
                "id": count,
                "pmid": paper.pmid,
                "name": str(paper),
                "paper_id": paper.id,
                "status": "present",
            }
            nodes[str(paper.pmid)] = node
            count += 1

        # Now generate links (relationships)
        for pmid, paper in nodes.copy().items():
            print(f"Parsing {pmid} relationships for graph.")
            paper["links"] = []
            for ref in get_paper_references(pmid):

                # If we have the node, make a relationship to it
                if ref["pmid"] in nodes:
                    paper["links"].append(ref["pmid"])

        # Save basic data to file
        data = {"nodes": list(nodes.values())}
        filename = "citation-nodes-with-included-links.json"
        data_file = os.path.join(paperbase, "templates", "data", filename)
        with open(data_file, "w") as fd:
            fd.writelines(json.dumps(data, indent=4))
