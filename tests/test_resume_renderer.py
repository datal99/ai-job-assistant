import unittest

from app.services.resume_renderer import escape_latex, render_summary


class LatexEscapingTests(unittest.TestCase):
    def test_escapes_each_latex_control_character_once(self):
        source = r"Python & C\C++: 100%_ready #1 $5 {ok} ~ ^"

        escaped = escape_latex(source)

        self.assertEqual(
            escaped,
            r"Python \& C\textbackslash{}C++: 100\%\_ready \#1 \$5 "
            r"\{ok\} \textasciitilde{} \textasciicircum{}",
        )

    def test_summary_uses_latex_escaping(self):
        self.assertEqual(
            render_summary("AI & platform engineer"),
            r"AI \& platform engineer",
        )


if __name__ == "__main__":
    unittest.main()
