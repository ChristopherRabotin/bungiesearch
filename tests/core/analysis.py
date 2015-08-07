from elasticsearch_dsl.analysis import analyzer, token_filter

edge_ngram_analyzer = analyzer(
    'edge_ngram_analyzer',
    type='custom',
    tokenizer='standard',
    filter=[
        'lowercase',
        token_filter(
            'edge_ngram_filter',
            type='edgeNGram',
            min_gram=2,
            max_gram=20
        )
    ]
)
