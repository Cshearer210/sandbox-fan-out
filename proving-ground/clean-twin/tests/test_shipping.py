from shipping import labels
def test_label(): assert labels.make_label('X') == 'LABEL-X'
