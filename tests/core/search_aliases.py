from core.models import Article
from bungiesearch.aliases import SearchAlias


class SearchTitle(SearchAlias):
    def alias_for(self, title):
        return self.search_instance.query('match', title=title)

    class Meta:
        models = (Article,)
        _alias_name = 'title_search'
