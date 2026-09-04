from board.text import file_citations, html_to_text, prose_without_citations


def test_light_html_becomes_marked_text():
    assert (
        html_to_text("It <b>works</b> via <code>/api/state</code> &amp; <em>more</em>.")
        == "It **works** via `/api/state` & _more_."
    )


def test_lists_become_lines():
    assert html_to_text("<ul><li>one</li><li>two</li></ul>") == "- one\n- two"


def test_file_spans_become_plain_paths_and_are_listed():
    deep = (
        'Prose. <span class="file">docs/plans/a.md</span><span class="file">docs/audits/b.md</span>'
    )
    assert file_citations(deep) == ["docs/plans/a.md", "docs/audits/b.md"]
    assert prose_without_citations(deep) == "Prose."
    assert html_to_text(deep) == "Prose. docs/plans/a.mddocs/audits/b.md"


def test_links_keep_their_target():
    assert html_to_text('see <a href="https://x.y">the page</a>') == "see the page (https://x.y)"


def test_an_angle_bracket_that_is_not_a_tag_survives():
    assert (
        html_to_text("stripe-python 8+ raises when a < b") == "stripe-python 8+ raises when a < b"
    )
