from reports import exporter
def test_export(): assert exporter.export([1,2]) == '1,2'
