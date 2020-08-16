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

        # Don't include papers we don't have
        include_missing = False

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
        links = []
        for pmid, paper in nodes.copy().items():
            print(f"Parsing {pmid} relationships for graph.")
            paper["links"] = []
            for ref in get_paper_references(pmid):

                # If we have the node, make a relationship to it
                if ref["pmid"] in nodes:
                    links.append(
                        {"source": paper["id"], "target": nodes[ref["pmid"]]["id"]}
                    )

                else:
                    if include_missing:
                        # If it's an external reference, add new node (will be hanging)
                        nodes[ref["pmid"]] = {
                            "id": count,
                            "pmid": ref["pmid"],
                            "name": ref["citation"],
                            "status": "missing",
                        }
                        count += 1
                    else:
                        paper["links"].append(ref)

        # Save basic data to file
        data = {"links": links, "nodes": list(nodes.values())}
        filename = (
            "papers-graph-nomissing.json"
            if not include_missing
            else "papers-graph.json"
        )
        data_file = os.path.join(paperbase, "templates", "data", filename)
        with open(data_file, "w") as fd:
            fd.writelines(json.dumps(data, indent=4))

        # Create new node and links for d3 neo4j format
        newnodes = []
        for _, node in nodes.items():
            node["description"] = node["name"]
            labels = ["Api"] if node["status"] == "missing" else ["Cookie"]
            newnodes.append(
                {"id": str(node["id"]), "labels": labels, "properties": node}
            )

        newlinks = []
        count = 0
        for link in links:
            newlinks.append(
                {
                    "id": count,
                    "type": "HAS_CITATION",
                    "startNode": str(link["source"]),
                    "endNode": str(link["target"]),
                }
            )
            count += 1

        # Save neo4j d3 formatted data to file (in future we want to put this in Google Storage?)
        data = {
            "results": [
                {
                    "columns": ["user", "entity"],
                    "data": [{"graph": {"nodes": newnodes, "relationships": newlinks}}],
                }
            ],
            "errors": [],
        }
        data_file = os.path.join(
            root, "apps", "common", "static", "data", "papers-graph-neo4j.json"
        )
        with open(data_file, "w") as fd:
            fd.writelines(json.dumps(data, indent=4))
