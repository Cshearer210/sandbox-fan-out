A miniature dbt-shaped project. Several green tests are dead canaries:
they pass whether the data is healthy or corrupt, because the model or the test config quietly
hides the rows a test would catch. deadcanary breaks the data to find which tests cannot fail.
