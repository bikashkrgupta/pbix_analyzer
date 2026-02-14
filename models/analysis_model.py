class AnalysisResult:

    def __init__(self):
        self.tables = set()
        self.columns = set()
        self.measures = set()

        self.used_columns = set()
        self.unused_columns = set()

        self.used_measures = set()
        self.unused_measures = set()

    def compute_summary(self):
        return {
            "Total Tables": len(self.tables),
            "Total Columns": len(self.columns),
            "Total Measures": len(self.measures),
            "Unused Columns": len(self.unused_columns),
            "Unused Measures": len(self.unused_measures)
        }

