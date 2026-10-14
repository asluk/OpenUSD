class ResolutionFailure(RuntimeError):
    def __init__(self, code, detail, **context):
        self.code, self.detail, self.context = code, detail, context
        super().__init__(f'{code}: {detail}')

    def result(self):
        return dict(success=False, code=self.code, detail=self.detail, **self.context)
