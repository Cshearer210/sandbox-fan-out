from inventory import warehouse
def sync():
    return warehouse.pull()
