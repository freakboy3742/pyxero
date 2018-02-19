"""
A small convenience class that takes the output of a report call to the Xero
API, and makes it a lot easier to access the values.

Key attributes are:
- .rows: the main body of the report, a list of lists.
- .columns: the column headers of the report. Useful for passing to other
            things to make a full table (e.g. to make a pandas DataFrame)
- .titles: Some background information about the report. Usually the name and
           the date it was run.
- .raw: the raw lists and dicts that was passed to the class

Indexing or iterating the object is the same as indexing or
iterating the body (rows)
"""


class XeroReport:
    """ A small convenience class that takes the output of a report call to
        the Xero API, and makes it a lot easier to access the values.
    """

    def __init__(self, report):
        self.raw = report
        self.titles = self._titles()
        self.columns = self._columns()
        self.rows = self._rows()

    def _titles(self):
        return self.raw[0]['ReportTitles']

    def _columns(self):
        data = self.raw
        data_columns_section = data[0]['Rows'][0]
        data_columns = [cell['Value'] for cell in data_columns_section['Cells']]
        return data_columns

    def _rows(self):
        data = self.raw
        data_contents = data[0]['Rows'][1:]
        data_sections = [record['Rows'] for record in data_contents]
        data_section_flattened = [item['Cells'] for sublist in data_sections
                                  for item in sublist]
        data_rows = [[cell['Value'] for cell in row]
                     for row in data_section_flattened]
        return data_rows

    def __repr__(self):
        titles = repr(self.titles)
        columns = repr(self.columns)
        rows = repr(self.rows)
        output = '\n'.join((titles, columns, rows))
        return output

    def __len__(self):
        return len(self.rows)

    def __iter__(self):
        return iter(self.rows)

    def __getitem__(self, key):
        return self.rows[key]
