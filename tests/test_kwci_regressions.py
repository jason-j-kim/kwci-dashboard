import math
import unittest

import pandas as pd

from kwci_pipeline import collectors, config, processor


class KwciRegressionTests(unittest.TestCase):
    def test_minmax_preserves_missing_values_in_constant_group(self):
        out = processor.minmax(pd.Series([math.nan, 7.0]))

        self.assertTrue(math.isnan(out.iloc[0]))
        self.assertEqual(out.iloc[1], 50.0)

    def test_customs_error_xml_is_not_treated_as_zero_export(self):
        xml = """
        <OpenAPI_ServiceResponse>
          <cmmMsgHeader>
            <returnReasonCode>30</returnReasonCode>
            <returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg>
          </cmmMsgHeader>
        </OpenAPI_ServiceResponse>
        """

        self.assertTrue(collectors._customs_response_error(xml))

    def test_score_panel_reweights_around_failed_sources(self):
        panel = pd.DataFrame([
            {
                "country": "US", "genre": "kpop", "survey_score": 10,
                "youtube_views": 999, "youtube_source": "youtube_api_error",
                "trends_interest": 10, "trends_source": "trends_api",
                "kf_count": 0, "kf_source": "kf_api_error_500",
                "export_usd": 123, "customs_source": "customs_api_error",
            },
            {
                "country": "JP", "genre": "kpop", "survey_score": 90,
                "youtube_views": 111, "youtube_source": "youtube_api",
                "trends_interest": 90, "trends_source": "trends_api",
                "kf_count": 60, "kf_source": "kf_api",
                "export_usd": 456, "customs_source": "customs_api",
            },
        ])

        scored, _ = processor.score_panel(panel)
        us = scored.loc[scored["country"] == "US"].iloc[0]

        self.assertTrue(math.isnan(us["youtube_norm"]))
        self.assertTrue(math.isnan(us["L1_norm"]))
        self.assertTrue(math.isnan(us["L2_norm"]))
        self.assertFalse(math.isnan(us["dsi"]))

    def test_domain_summary_reports_active_and_industry_weights(self):
        scored = pd.DataFrame({
            "genre": list(config.GENRE_WEIGHTS),
            "dsi": [50.0] * len(config.GENRE_WEIGHTS),
        })

        summary = processor.domain_summary(scored).set_index("genre")

        self.assertEqual(summary.loc["kbeauty", "domain_weight"], processor.active_weights()["kbeauty"])
        self.assertEqual(summary.loc["kbeauty", "industry_weight"], config.GENRE_WEIGHTS["kbeauty"])


if __name__ == "__main__":
    unittest.main()
