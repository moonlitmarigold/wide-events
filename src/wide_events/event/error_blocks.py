from .blocks import EventBlock

class ExceptionEvent(EventBlock):
    """Writes an error at the top level of the `LogContext` event, as `error: {type, message, stack}`."""

    namespace = "error"
    use_namespace_on_write = False
    append_list = True

    @classmethod
    def save_error(cls, _type, message, stack):
        """Write `error: {type: _type, message, stack}` to the current event."""
        return cls.from_kwargs(
            error={
                "type": _type,
                "message": message,
                "stack": stack
            }
        )

class HookErrorEvent(EventBlock):
    """Appends hook failures at the top level of the `LogContext` event, as `hook_errors: [{hook, stack}, ...]`."""

    namespace = "hook_error"
    use_namespace_on_write = False
    append_list = True

    @classmethod
    def save_hook_error(cls, label, stack):
        """Append `{hook: label, stack}` to `hook_errors` in the current event."""
        return cls.from_kwargs(
            hook_errors=[{
                "hook": label,
                "stack": stack
            }]
        )
