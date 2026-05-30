from elasticsearch import Elasticsearch


class ElasticRepo:

    def __init__(
        self,
        elastic_client: Elasticsearch
    ) -> None:
        self.elastic_client = elastic_client

    def get_lectures_id_by_term_and_date(
        self,
        term: str,
        date_from: str,
        date_to: str
    ) -> list[str]:
        query_body = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": term,
                                "fields": ["title^3", "annotation^2", "content_text"],
                                "type": "best_fields",
                                "operator": "and",
                            }
                        }
                    ],
                    "filter": [{"range": {"date": {"gte": date_from, "lte": date_to}}}],
                }
            },
            "_source": ["lecture_id"],
        }

        response = self.elastic_client.search(index="lectures", body=query_body, size=1000)
        lecture_ids = [hit["_source"]["lecture_id"] for hit in response["hits"]["hits"]]
        return lecture_ids
