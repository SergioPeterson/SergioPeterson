import datetime as dt
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import generate


class AgeTests(unittest.TestCase):
    def test_exact_age_in_years_months_and_days(self):
        born = dt.date(2002, 1, 10)
        self.assertEqual(
            generate.calculate_age_parts(born, dt.date(2026, 1, 9)),
            (23, 11, 30),
        )
        self.assertEqual(
            generate.calculate_age_parts(born, dt.date(2026, 1, 10)),
            (24, 0, 0),
        )
        self.assertEqual(
            generate.calculate_age_parts(born, dt.date(2026, 7, 10)),
            (24, 6, 0),
        )

    def test_age_uses_singular_unit_labels(self):
        self.assertEqual(
            generate.format_age(
                dt.date(2002, 1, 10),
                dt.date(2003, 2, 11),
            ),
            "1 year, 1 month, 1 day",
        )


class FormattingTests(unittest.TestCase):
    def test_formats_large_and_negative_numbers(self):
        self.assertEqual(generate.format_number(999), "999")
        self.assertEqual(generate.format_number(1234), "1,234")
        self.assertEqual(generate.format_number(-12005), "-12,005")

    def test_xml_text_is_escaped(self):
        svg = generate.render_svg(
            "dark",
            ["<&"],
            generate.ProfileStats(
                owned_repos=1,
                contributed_repos=2,
                stars=3,
                commits=4,
                followers=5,
                additions=6,
                deletions=7,
            ),
            today=dt.date(2026, 1, 10),
        )
        self.assertIn("&lt;&amp;", svg)
        ET.fromstring(svg)


class GraphQLAggregationTests(unittest.TestCase):
    def test_aggregates_history_and_repository_pages(self):
        responses = {
            None: {
                "repository": {
                    "defaultBranchRef": {
                        "target": {
                            "history": {
                                "nodes": [
                                    {"additions": 10, "deletions": 2},
                                    {"additions": 5, "deletions": 8},
                                ],
                                "pageInfo": {
                                    "hasNextPage": True,
                                    "endCursor": "commits-2",
                                },
                            }
                        }
                    }
                }
            },
            "commits-2": {
                "repository": {
                    "defaultBranchRef": {
                        "target": {
                            "history": {
                                "nodes": [{"additions": 7, "deletions": 1}],
                                "pageInfo": {
                                    "hasNextPage": False,
                                    "endCursor": None,
                                },
                            }
                        }
                    }
                }
            },
        }

        totals = generate.aggregate_commit_history(
            lambda cursor: responses[cursor]
        )

        self.assertEqual(totals.commits, 3)
        self.assertEqual(totals.additions, 22)
        self.assertEqual(totals.deletions, 11)

    def test_stops_if_api_repeats_a_cursor(self):
        page = {
            "repository": {
                "defaultBranchRef": {
                    "target": {
                        "history": {
                            "nodes": [{"additions": 1, "deletions": 1}],
                            "pageInfo": {
                                "hasNextPage": True,
                                "endCursor": "same",
                            },
                        }
                    }
                }
            }
        }

        with self.assertRaisesRegex(RuntimeError, "cursor"):
            generate.aggregate_commit_history(lambda cursor: page)


class RenderingTests(unittest.TestCase):
    def test_both_themes_include_complete_profile_and_stats(self):
        stats = generate.ProfileStats(1, 2, 3, 4, 5, 6, 7)
        required = (
            "Sergio W. Peterson",
            "Founding Engineer",
            "Mars Accounting / Minerva Intelligence",
            "AI &amp; Robotics Engineer",
            "Uptime",
            "24 years, 0 months, 0 days",
            "Python",
            "PyTorch",
            "TypeScript",
            "React",
            "ROS",
            "Docker",
            "AWS",
            "Robot learning",
            "VLM systems",
            "Evaluation infrastructure",
            "sergiopeterson.dev",
            "linkedin.com/in/sergio-w-peterson",
            "sergiopeterson.dev@gmail.com",
            "Owned Repos",
            "Contributed Repos",
            "Stars",
            "Commits",
            "Followers",
            "Net Lines",
            "Additions (++)",
            "Deletions (--)",
            "Public default-branch data",
        )

        for theme in ("dark", "light"):
            with self.subTest(theme=theme):
                svg = generate.render_svg(
                    theme,
                    ["portrait"],
                    stats,
                    today=dt.date(2026, 1, 10),
                )
                ET.fromstring(svg)
                self.assertIn("white-space:pre", svg)
                for text in required:
                    self.assertIn(text, svg)

    def test_rejects_unknown_theme(self):
        with self.assertRaises(ValueError):
            generate.render_svg(
                "sepia",
                [],
                generate.ProfileStats(0, 0, 0, 0, 0, 0, 0),
                today=dt.date(2026, 1, 10),
            )

    def test_readme_uses_absolute_raw_theme_urls(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        base = "https://raw.githubusercontent.com/SergioPeterson/SergioPeterson/master/"
        self.assertIn(f'{base}dark_mode.svg', readme)
        self.assertIn(f'{base}light_mode.svg', readme)


if __name__ == "__main__":
    unittest.main()
