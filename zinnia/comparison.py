"""Comparison tools for Zinnia"""
from django.utils import six
from django.core.cache import caches
from django.core.cache import InvalidCacheBackendError

from math import sqrt

from zinnia.settings import F_MIN
from zinnia.settings import F_MAX


def pearson_score(list1, list2):
    """
    Compute the Pearson' score between 2 lists of vectors.
    """
    sum1 = sum(list1)
    sum2 = sum(list2)
    sum_sq1 = sum([pow(l, 2) for l in list1])
    sum_sq2 = sum([pow(l, 2) for l in list2])

    prod_sum = sum([list1[i] * list2[i] for i in range(len(list1))])

    num = prod_sum - (sum1 * sum2 / len(list1))
    den = sqrt((sum_sq1 - pow(sum1, 2.0) / len(list1)) *
               (sum_sq2 - pow(sum2, 2.0) / len(list2)))

    if den == 0.0:
        return 1.0

    return num / den


class ClusteredModel(object):
    """
    Wrapper around Model class
    building a dataset of instances.
    """

    def __init__(self, queryset, fields):
        self.fields = fields
        self.queryset = queryset

    def dataset(self):
        """
        Generate a dataset based on the queryset
        and the specified fields.
        """
        dataset = {}
        for item in self.queryset.values_list(*(['pk'] + self.fields)):
            item = list(item)
            item_pk = item.pop(0)
            dataset[item_pk] = ' '.join(map(six.text_type, item))
        return dataset


class VectorBuilder(object):
    """
    Build a list of vectors based on datasets.
    """

    def __init__(self, queryset, fields):
        self.key = ''
        self._columns = []
        self._dataset = {}
        self.clustered_model = ClusteredModel(queryset, fields)

    def build_dataset(self):
        """
        Generate the whole dataset.
        """
        data = {}
        words_total = {}

        model_data = self.clustered_model.dataset()
        for instance, words in model_data.items():
            words_item_total = {}
            for word in words.split():
                word = word.lower()
                words_total.setdefault(word, 0)
                words_item_total.setdefault(word, 0)
                words_total[word] += 1
                words_item_total[word] += 1
            data[instance] = words_item_total

        top_words = []
        for word, count in words_total.items():
            frequency = float(count) / len(data)
            if frequency > F_MIN and frequency < F_MAX:
                top_words.append(word)

        self._dataset = {}
        self._columns = top_words
        for instance in data.keys():
            self._dataset[instance] = [data[instance].get(word, 0)
                                       for word in top_words]
        self.key = self.generate_key()

    def generate_key(self):
        """
        Generate key for this list of vectors.
        """
        return self.clustered_model.queryset.count()

    def flush(self):
        """
        Flush the dataset if required.
        """
        if self.key != self.generate_key():
            self.build_dataset()
        return self._columns, self._dataset

    @property
    def columns(self):
        """
        Access to columns in a secure manner.
        """
        return self.flush()[0]

    @property
    def dataset(self):
        """
        Access to dataset in a secure manner.
        """
        return self.flush()[1]


def compute_related(object_id, dataset):
    """
    Compute related pks to an object with a dataset.
    """
    object_vector = dataset.get(object_id)
    if not object_vector:
        return []

    object_related = {}
    for o_id, o_vector in dataset.items():
        if o_id != object_id:
            score = pearson_score(object_vector, o_vector)
            if score:
                object_related[o_id] = score

    related = sorted(object_related.items(),
                     key=lambda k_v: (k_v[1], k_v[0]))
    return [rel[0] for rel in related]


def get_comparison_cache():
    """
    Try to access to ``zinnia_comparison`` cache backend,
    if fail use the ``default`` cache backend.
    """
    try:
        comparison_cache = caches['zinnia_comparison']
    except InvalidCacheBackendError:
        comparison_cache = caches['default']
    return comparison_cache
