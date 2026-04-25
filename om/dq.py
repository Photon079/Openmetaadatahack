from .client import OMClient


class DQFetcher:
    def __init__(self, client: OMClient):
        self.client = client

    def _fetch_all_test_cases(self) -> list:
        """Paginate through all test cases, requesting testDefinition + testSuite fields."""
        test_cases = []
        endpoint = "/dataQuality/testCases"
        params = {"limit": 100, "fields": "testDefinition,testSuite"}
        while True:
            data = self.client.get(endpoint, params=params)
            test_cases.extend(data.get("data", []))
            paging = data.get("paging", {})
            if "after" in paging:
                params["after"] = paging["after"]
            else:
                break
        return test_cases

    def _domain_matches(self, tc: dict, domain_filter: str) -> bool:
        """Return True if this test case belongs to the requested domain (case-insensitive)."""
        domain_obj = tc.get("domain") or {}
        domain_name = (
            domain_obj.get("displayName")
            or domain_obj.get("name")
            or domain_obj.get("fullyQualifiedName")
            or ""
        )
        return domain_filter.lower() in domain_name.lower()

    def fetch_failed_tests(self, start_ts: int, end_ts: int, domain: str = None) -> list:
        """
        Fetch failed DQ test results in [start_ts, end_ts] (Unix ms).
        Optionally filter by domain name (substring match, case-insensitive).
        """
        all_failed_results = []

        # 1. Pull every test case (with owner/domain metadata)
        test_cases = self._fetch_all_test_cases()

        # 2. Optionally filter by domain
        if domain:
            test_cases = [tc for tc in test_cases if self._domain_matches(tc, domain)]
            print(f"   [domain filter '{domain}'] → {len(test_cases)} test cases in scope")

        # 3. Fetch failed results for each test case in the time window
        table_tags_cache = {}
        for tc in test_cases:
            fqn = tc.get("fullyQualifiedName")
            if not fqn:
                continue

            # Extract table FQN to fetch its tags (service.db.schema.table.testName)
            parts = fqn.split(".")
            if len(parts) >= 2:
                table_fqn = ".".join(parts[:-1])
                if table_fqn not in table_tags_cache:
                    try:
                        # Make API call to get tags
                        table_data = self.client.get(f"/tables/name/{table_fqn}", params={"fields": "tags"})
                        tags = [t.get("tagFQN", "") for t in table_data.get("tags", [])]
                        table_tags_cache[table_fqn] = tags
                    except Exception as e:
                        table_tags_cache[table_fqn] = []
                        print(f"   Warning: could not fetch tags for {table_fqn}: {e}")
                
                tc["table_tags"] = table_tags_cache[table_fqn]

            endpoint = f"/dataQuality/testCases/{fqn}/testCaseResult"
            params = {
                "startTs": start_ts,
                "endTs": end_ts,
                "testCaseStatus": "Failed",
                "limit": 100,
            }

            try:
                data = self.client.get(endpoint, params=params)
                for r in data.get("data", []):
                    r["testCase"] = tc
                    all_failed_results.append(r)
            except Exception as e:
                print(f"   Warning: could not fetch results for {fqn}: {e}")

        return all_failed_results
