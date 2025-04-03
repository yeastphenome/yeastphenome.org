from yeastphenome.settings import ENTREZ_EMAIL
from Bio import Entrez


def get_pubmed_paper(pmid):
    """A shared function to retrieve the Paper in xml"""
    Entrez.email = ENTREZ_EMAIL
    handle = Entrez.efetch(db="pubmed", id=[str(pmid)], retmode="xml")
    return Entrez.read(handle)


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

    pgn = ""
    if "Pagination" in article.keys():
        pgn = article["Pagination"]["MedlinePgn"]

    vol = ""
    if "Volume" in article["Journal"]["JournalIssue"].keys():
        vol = article["Journal"]["JournalIssue"]["Volume"]

    jrn = ""
    if "ISOAbbreviation" in article["Journal"].keys():
        jrn = article["Journal"]["ISOAbbreviation"]

    citation = u"%s %s; %s" % (jrn, pubdate, vol)
    if pgn:
        citation += u":%s" % pgn

    abstract = ""
    if "Abstract" in article:
        abstract = article["Abstract"]["AbstractText"][0]

    return {
        "title": article["ArticleTitle"],
        "authors": authors_list,
        "abstract": abstract,
        "citation": citation,
    }
