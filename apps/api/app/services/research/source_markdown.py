"""Keep source examples intact while the article extractor selects the main text."""
import re
import uuid
from bs4 import BeautifulSoup

MAX_TABLE_ROWS = 200
MAX_TABLE_COLUMNS = 100
MAX_TABLE_CELLS = 10_000
MAX_TABLE_TEXT_CHARS = 200_000


class TableTooLarge(ValueError):
    pass


def protect_examples(html: str) -> tuple[str, dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    for figure in soup.find_all("figure"):
        if figure.find(["pre", "code", "table"]):
            figure.unwrap()
    replacements = {}
    prefix = 'CE' + uuid.uuid4().hex + 'BLOCK'
    # Tables and code are opaque to extractors, which otherwise flatten their structure.
    for element in list(soup.find_all(['pre', 'table'])):
        if element.parent is None or element.find_parent(['pre', 'table']):
            continue
        if element.name == 'pre':
            code = element.find('code') or element
            value = code.get_text('', strip=False).strip('\n')
            language = ''
            for node in (code, element, element.parent):
                classes = ' '.join(node.get('class', []))
                match = re.search(r'(?:language-|lang-|highlight-source-)([\w+-]+)', classes)
                language = language or (match.group(1) if match else node.get('data-language', '') or node.get('data-lang', ''))
            language = language if re.fullmatch(r'[\w+-]+', language) else 'text'
            marker = '`' * max(3, max((len(s) + 1 for s in re.findall(r'`+', value)), default=3))
            rendered = f'{marker}{language or "text"}\n{value}\n{marker}'
        else:
            try:
                rows = table_grid(element)
            except TableTooLarge:
                placeholder = soup.new_tag('p')
                placeholder.string = '[Tabela pominięta: przekroczony limit ekstrakcji.]'
                element.replace_with(placeholder)
                continue
            rows = [row for row in rows if row]
            if not rows:
                continue
            width = max(map(len, rows))
            # A missing header is left empty; no invented labels or numeric alignment.
            has_header = bool(element.find('tr').find('th'))
            if not has_header:
                rows.insert(0, [''] * width)
            lines = ['| ' + ' | '.join(row + [''] * (width-len(row))) + ' |' for row in rows]
            lines.insert(1, '| ' + ' | '.join(['---'] * width) + ' |')
            rendered = '\n'.join(lines)
        token = f'{prefix}{len(replacements)}TOKEN'
        replacements[token] = rendered
        placeholder = soup.new_tag('p')
        placeholder.string = token
        element.replace_with(placeholder)
    for code in soup.find_all('code'):
        value = code.get_text('', strip=False)
        marker = '`' * max(1, max((len(s)+1 for s in re.findall(r'`+', value)), default=1))
        # Padding makes values containing literal backticks valid inline Markdown.
        token = f'{prefix}{len(replacements)}TOKEN'
        replacements[token] = f'{marker} {value} {marker}' if '`' in value else f'{marker}{value}{marker}'
        code.replace_with(token)
    return str(soup), replacements


def restore_examples(text: str, replacements: dict[str, str]) -> str:
    for token, value in replacements.items():
        text = text.replace(token, value)
    return text


def table_grid(table) -> list[list[str]]:
    source_rows = [row for row in table.find_all('tr') if row.find_parent('table') is table]
    if len(source_rows) > MAX_TABLE_ROWS:
        raise TableTooLarge
    grid: dict[tuple[int, int], str] = {}
    width = 0
    expanded_text_chars = 0
    def span(cell, name, remaining):
        try:
            number = int(cell.get(name, 1))
        except (TypeError, ValueError):
            number = 1
        # HTML rowspan=0 spans the remaining rows; colspan=0 is invalid (treated as 1).
        if name == "colspan" and number > remaining:
            raise TableTooLarge
        if number == 0:
            number = remaining if name == "rowspan" else 1
        return min(remaining, max(1, number))
    for row_index, row in enumerate(source_rows):
        column = 0
        for cell in row.find_all(['th', 'td'], recursive=False):
            while (row_index, column) in grid:
                column += 1
            colspan = span(cell, 'colspan', MAX_TABLE_COLUMNS)
            rowspan = span(cell, 'rowspan', len(source_rows) - row_index)
            expanded_width = max(width, column + colspan)
            if expanded_width > MAX_TABLE_COLUMNS or expanded_width * len(source_rows) > MAX_TABLE_CELLS:
                raise TableTooLarge
            value = cell.get_text(' ', strip=True).replace('|', '\\|').replace('\n', ' ')
            expanded_text_chars += (len(value) + 3) * rowspan * colspan
            if expanded_text_chars > MAX_TABLE_TEXT_CHARS:
                raise TableTooLarge
            for y in range(row_index, row_index + rowspan):
                for x in range(column, column + colspan):
                    grid[y, x] = value
            column += colspan
            width = max(width, column)
    return [[grid.get((y, x), '') for x in range(width)] for y in range(len(source_rows))]
