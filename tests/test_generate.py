import datetime as dt
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import generate

PORTRAIT = [[("#", "#c0ffee")]]


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
            [[("<&", "#c0ffee")]],
            generate.ProfileStats(1, 2, 3, 4, 5, 6, 7),
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
            "sergio@peterson",
            "Sergio W. Peterson",
            "OS",
            "Uptime",
            "24 years, 0 months, 0 days",
            "Host",
            "Mars Accounting / Minerva Intelligence",
            "Kernel",
            "Founding Engineer",
            "IDE",
            "Cursor, VS Code, Jupyter",
            "Focus",
            "VLM systems, evaluation infrastructure",
            "Languages.Programming",
            "Python",
            "PyTorch",
            "TypeScript",
            "React",
            "ROS",
            "FastAPI",
            "Languages.Platforms",
            "Docker, AWS, Linux",
            "Languages.Computer",
            "HTML, CSS, JSON, YAML, LaTeX",
            "Languages.Real",
            "English",
            "Hobbies.Software",
            "Robot learning",
            "Agent systems",
            "Hobbies.Hardware",
            "Robotics, autonomous racing",
            "- Contact",
            "sergiopeterson.dev",
            "linkedin.com/in/sergio-w-peterson",
            "sergiopeterson.dev@gmail.com",
            "San Francisco, CA",
            "- GitHub Stats",
            "Repos",
            "Contributed",
            "Stars",
            "Followers",
            "Commits",
            "Lines of Code on GitHub",
            "++",
            "--",
            'class="key"',
            'class="value"',
            'class="add"',
            'class="del"',
        )

        for theme in ("dark", "light"):
            with self.subTest(theme=theme):
                svg = generate.render_svg(
                    theme,
                    PORTRAIT,
                    stats,
                    today=dt.date(2026, 1, 10),
                )
                root = ET.fromstring(svg)
                self.assertIn("white-space:pre", svg)
                self.assertIn('width="985px"', svg)
                self.assertIn('height="530px"', svg)
                self.assertIn('font-size="15px"', svg)
                self.assertIn('xml:space="preserve"', svg)
                self.assertIn("\u00a0", svg)
                self.assertNotIn("$ whoami", svg)
                self.assertNotIn("<circle", svg)
                self.assertIn('<text class="portrait">', svg)
                self.assertIn('fill="#c0ffee"', svg)
                self.assertNotIn("<image", svg)
                self.assertNotIn("data:image/png;base64", svg)
                for text in required:
                    self.assertIn(text, svg)

                namespace = "{http://www.w3.org/2000/svg}"
                for text_element in root.iter(f"{namespace}text"):
                    if text_element.get("x") == "390":
                        rendered_text = "".join(text_element.itertext())
                        self.assertLessEqual(len(rendered_text), 64)

    def test_ascii_portrait_fits_left_column(self):
        portrait = json.loads(Path("portrait.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(portrait), 38)
        self.assertLessEqual(len(portrait), 42)
        self.assertLessEqual(
            max(sum(len(text) for text, _ in row) for row in portrait),
            84,
        )
        allowed = set("@%#*+=-:. /\\|")
        self.assertTrue(
            all(set(text) <= allowed for row in portrait for text, _ in row)
        )
        rows = ["".join(text for text, _ in row) for row in portrait]
        non_space = sum(character != " " for row in rows for character in row)
        self.assertLess(non_space / (len(rows) * 84), 0.42)
        stabilizer_widths = [
            sum(character != " " for character in row[68:]) for row in rows
        ]
        self.assertLessEqual(max(stabilizer_widths), 3)
        self.assertGreaterEqual(sum(stabilizer_widths), 10)
        self.assertFalse(Path("portrait.txt").exists())
        self.assertFalse(Path("portrait_halftone.png").exists())

    def test_rejects_unknown_theme(self):
        with self.assertRaises(ValueError):
            generate.render_svg(
                "sepia",
                PORTRAIT,
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
