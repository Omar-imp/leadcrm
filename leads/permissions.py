"""
Maps each role to the CRM sections it's allowed to access.
'admin' and 'ceo' get everything. Everyone else is restricted.
"""

ROLE_PERMISSIONS = {
    'admin': ['*'],
    'ceo': ['*'],
    'sales_manager': [
        'dashboard', 'leads', 'pipeline', 'quotations', 'contacts',
        'payments', 'followups', 'communications', 'reports',
        'meetings', 'tasks', 'activity',
    ],
    'sales_executive': [
        'dashboard', 'leads', 'pipeline', 'followups',
        'meetings', 'tasks', 'communications', 'contacts',
    ],
    'project_manager': [
        'dashboard', 'projects', 'tasks', 'meetings',
        'documents', 'contracts', 'communications', 'contacts',
    ],
    'support_agent': [
        'dashboard', 'tickets', 'communications', 'contacts',
    ],
    'finance': [
        'dashboard', 'payments', 'quotations', 'contracts', 'reports',
    ],
}

# Maps each "section" key to the URL prefixes that belong to it
URL_SECTION_MAP = {
    'dashboard': ['/'],
    'users': ['/users/'],
    'leads': ['/leads/'],
    'pipeline': ['/pipeline/', '/opportunities/'],
    'quotations': ['/quotations/'],
    'contacts': ['/companies/', '/contacts/'],
    'payments': ['/payments/'],
    'followups': ['/followups/'],
    'communications': ['/communications/'],
    'reports': ['/reports/'],
    'meetings': ['/meetings/'],
    'tasks': ['/tasks/'],
    'projects': ['/projects/', '/milestones/'],
    'documents': ['/documents/'],
    'contracts': ['/contracts/'],
    'support': ['/tickets/'],
    'activity': ['/activity/'],
    'notifications': ['/notifications/'],
}


def get_allowed_sections(role):
    """Returns the list of section keys this role can access."""
    return ROLE_PERMISSIONS.get(role, [])


def get_section_for_path(path):
    """Given a URL path, find which section it belongs to."""
    for section, prefixes in URL_SECTION_MAP.items():
        for prefix in prefixes:
            if prefix == '/' and path == '/':
                return section
            if prefix != '/' and path.startswith(prefix):
                return section
    return None


def is_path_allowed(role, path):
    """Check if a role is allowed to access a given URL path."""
    allowed = get_allowed_sections(role)
    if '*' in allowed:
        return True
    # always allow login/logout/admin/static/media regardless of role
    if path.startswith('/login') or path.startswith('/logout') or \
       path.startswith('/admin') or path.startswith('/static') or \
       path.startswith('/media'):
        return True
    section = get_section_for_path(path)
    if section is None:
        # unmapped paths (e.g. detail pages with IDs) - check their prefix manually
        return True
    return section in allowed