from core.models import Article
from bungiesearch.aliases import SearchAlias


class SearchTitle(SearchAlias):
    def alias_for(self, title):
        return self.search_instance.query('match', title=title)

    class Meta:
        models = (Article,)
        alias_name = 'title_search'

class InvalidAlias(SearchAlias):
    def alias_for_does_not_exist(self, title):
        return title

    class Meta:
        models = (Article,)
