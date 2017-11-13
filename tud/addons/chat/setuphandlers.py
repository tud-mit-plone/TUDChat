
def uninstall(context):
    """Uninstall that removes our base profiles"""
    # see https://github.com/collective/example.p4p5/issues/12

    profile_id = 'profile-tud.addons.chat:install-base'
    context = context._getImportContext(profile_id)

    gs = context.getSite().portal_setup
    if u'tud.addons.chat:install-base' in gs._profile_upgrade_versions:
        del(gs._profile_upgrade_versions[u'tud.addons.chat:install-base'])

    if u'tud.addons.chat:uninstall-base' in gs._profile_upgrade_versions:
        del(gs._profile_upgrade_versions[u'tud.addons.chat:uninstall-base'])