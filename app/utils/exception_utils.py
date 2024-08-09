# -*- coding: utf-8 -*-
import traceback


class ExceptionUtils:
    @classmethod
    def exception_traceback(cls, e):
        # print(f"\nException: {str(e)}\nCallstack:\n{traceback.format_exc()}\n")
        import log
        log.error(f"\nException: {str(e)}\nCallstack:\n{traceback.format_exc()}\n")
