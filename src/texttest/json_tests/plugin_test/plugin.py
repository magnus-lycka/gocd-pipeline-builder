# noinspection PyUnusedLocal
def custom_add_pipeline(go=None, operation=None, **kwargs):
    go.create_a_pipeline(operation)

action_plugins = {'my-new-plugin': custom_add_pipeline}
