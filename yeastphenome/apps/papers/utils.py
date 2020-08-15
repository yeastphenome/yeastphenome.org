from yeastphenome.settings import ENTREZ_EMAIL
from Bio import Entrez
from yeastphenome.apps.papers.models import Paper


def get_pubmed_paper(pmid):
    """A shared function to retrieve the Paper in xml
    """
    Entrez.email = ENTREZ_EMAIL
    handle = Entrez.efetch(db="pubmed", id=[str(pmid)], retmode="xml")
    return Entrez.read(handle)


def get_paper_references(pmid, xml_data=None):
    """Get references that are provided given a given pmid. The user can optionally
       pass in the xml_data (already retrieved) so we can share one call between
       functions.
    """
    if xml_data is None:
        xml_data = get_pubmed_paper(pmid)

    # Some papers don't have references here it seems!
    if not xml_data["PubmedArticle"][0]["PubmedData"]["ReferenceList"]:
        return []

    refs = xml_data["PubmedArticle"][0]["PubmedData"]["ReferenceList"][0]["Reference"]

    # Stay in the namespace of pmid (in testing all are pubmed)
    # Also checked that each only has one id in the list
    refs = [
        {"citation": ref["Citation"], "pmid": str(ref["ArticleIdList"][0])}
        for ref in refs
        if ref["ArticleIdList"][0].attributes["IdType"] == "pubmed"
    ]

    # Return list of dicts with {"citation": ... , "pmid": ...}
    return refs


def get_paper_references_context(paper, xml_data=None):
    """Generate the same references, but return the correct context to generate
       the graph
    """
    refs = get_paper_references(paper.pmid, xml_data)

    # Find refs that we have in the database
    haves = [int(p["pmid"]) for p in refs]
    citations_we_have = Paper.objects.filter(pmid__in=haves)

    # Remove pmids that we have from listing
    citations_missing = [ref for ref in refs if ref["pmid"] not in haves]

    # Generate d3 nodes and links
    nodes = [{"name": str(paper), "pmid": paper.pmid, "id": 0, "status": "root"}]
    count = 1
    for node in citations_we_have:
        nodes.append(
            {
                "name": str(node),
                "pmid": node.pmid,
                "id": count,
                "status": "present",
                "paper_id": node.id,
            }
        )
        count += 1
    for node in citations_missing:
        nodes.append(
            {
                "name": node["citation"].split(";")[0],
                "pmid": node["pmid"],
                "id": count,
                "status": "missing",
            }
        )
        count += 1

    # Skip first (central) node, main paper
    links = []
    for node in nodes[1:]:
        links.append({"source": 0, "target": node["id"], "value": 10})

    # Return context with enough to generate single linked graph
    return {
        "citation_nodes": nodes,
        "citation_links": links,
        "paper": paper,
    }


def get_pubmed_paper_context(pmid, xml_data=None):
    """Given a Pubmed identifier (pmid) use the Pubmed API (Entrez) to return
       metadata about the paper
    """
    if xml_data is None:
        xml_data = get_pubmed_paper(pmid)
    article = xml_data.get("PubmedArticle")[0].get("MedlineCitation").get("Article")
    authors_list = [
        (u"%s %s" % (author["ForeName"], author["LastName"]))
        for author in article["AuthorList"]
    ]

    pubdate = ""
    if "Year" in article["Journal"]["JournalIssue"]["PubDate"]:
        pubdate = article["Journal"]["JournalIssue"]["PubDate"]["Year"]
    elif "MedlineDate" in article["Journal"]["JournalIssue"]["PubDate"]:
        pubdate = article["Journal"]["JournalIssue"]["PubDate"]["MedlineDate"]

    pgn = "."
    if "Pagination" in article.keys():
        pgn = article["Pagination"]["MedlinePgn"]

    vol = ""
    if "Volume" in article["Journal"]["JournalIssue"].keys():
        vol = article["Journal"]["JournalIssue"]["Volume"]

    return {
        "title": article["ArticleTitle"],
        "authors": authors_list,
        "abstract": article["Abstract"]["AbstractText"][0],
        "citation": u"%s %s; %s:%s"
        % (article["Journal"]["ISOAbbreviation"], pubdate, vol, pgn),
    }
