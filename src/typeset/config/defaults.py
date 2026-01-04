"""Default configuration values."""

DEFAULT_CONFIG_YAML = """\
# Typeset Configuration
# For full documentation, see: https://github.com/yourname/typeset

metadata:
  title: "My Book Title"
  subtitle: null
  authors:
    - "Author Name"
  publisher: null
  publication_date: null
  isbn_print: null
  isbn_epub: null
  language: "en"
  description: null
  keywords: []
  copyright: null

pdf:
  # Page setup - common sizes:
  # "6in 9in" (trade paperback), "5.5in 8.5in" (digest), "5in 8in" (mass market)
  page_size: "6in 9in"
  margins:
    top: "0.75in"
    bottom: "0.75in"
    inside: "0.875in"   # Gutter for binding
    outside: "0.625in"
  bleed: "0.125in"      # Set to null for no bleed
  crop_marks: true

  # Typography
  font_family: "Georgia, serif"
  font_size: "11pt"
  line_height: 1.5

  # Headers and footers
  show_page_numbers: true
  page_number_position: "bottom-outside"  # or "bottom-center"
  show_running_headers: true

  # Front matter
  include_title_page: true
  include_copyright_page: true
  include_toc: true

  # Advanced
  embed_fonts: true

epub:
  version: "3.0"        # or "2.0" for older readers
  language: "en"
  split_chapters: true
  include_toc: true
  css_file: null        # Path to custom CSS
  font_size: "1em"
  cover_image: null     # Path to cover image
  generate_cover: false

# Map Word styles to semantic elements
style_mapping:
  chapter_heading_styles:
    - "Heading 1"
    - "Title"
    - "Chapter"
  section_heading_styles:
    - "Heading 2"
    - "Heading 3"
    - "Heading 4"
  body_styles:
    - "Normal"
    - "Body Text"
    - "Body"
  blockquote_styles:
    - "Quote"
    - "Block Text"

output_dir: "./output"
"""
