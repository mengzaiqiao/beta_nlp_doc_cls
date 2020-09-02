import csv
import sys
import torch
from nltk.tokenize import sent_tokenize
from torch.utils.data import DataLoader, RandomSampler, TensorDataset


class InputExample(object):
    """A single training/test example for simple sequence classification."""

    def __init__(self, guid, text_a, text_b=None, label=None):
        """Constructs a InputExample.
        Args:
            guid: Unique id for the example.
            text_a: string. The untokenized text of the first sequence. For single
            sequence tasks, only this sequence must be specified.
            text_b: (Optional) string. The untokenized text of the second sequence.
            Only must be specified for sequence pair tasks.
            label: (Optional) string. The label of the example. This should be
            specified for train and dev examples, but not for test examples.
        """
        self.guid = guid
        self.text_a = text_a
        self.text_b = text_b
        self.label = label


class InputFeatures(object):
    """A single set of features of data."""

    def __init__(self, input_ids, input_mask, segment_ids, label_id):
        self.input_ids = input_ids
        self.input_mask = input_mask
        self.segment_ids = segment_ids
        self.label_id = label_id


class BertProcessor(object):
    """Base class for data converters for sequence classification data sets."""

    def get_train_examples(self, data_dir):
        """
        Gets a collection of `InputExample`s for the train set
        :param data_dir:
        :return:
        """
        raise NotImplementedError()

    def get_dev_examples(self, data_dir):
        """
        Gets a collection of `InputExample`s for the dev set
        :param data_dir:
        :return:
        """
        raise NotImplementedError()

    def get_test_examples(self, data_dir):
        """
        Gets a collection of `InputExample`s for the test set
        :param data_dir:
        :return:
        """
        raise NotImplementedError()

    def get_labels(self):
        """
        Gets a list of possible labels in the dataset
        :return:
        """
        raise NotImplementedError()

    @classmethod
    def _read_tsv(cls, input_file, quotechar=None):
        """
        Reads a Tab Separated Values (TSV) file
        :param input_file:
        :param quotechar:
        :return:
        """
        with open(input_file, "r") as f:
            reader = csv.reader(f, delimiter="\t", quotechar=quotechar)
            lines = []
            for line in reader:
                if sys.version_info[0] == 2:
                    line = list(str(cell, "utf-8") for cell in line)
                lines.append(line)
            return lines

def _truncate_seq_pair(tokens_a, tokens_b, max_length):
    """
    Truncates a sequence pair in place to the maximum length
    :param tokens_a:
    :param tokens_b:
    :param max_length:
    :return:
    """

    # This is a simple heuristic which will always truncate the longer sequence
    # one token at a time. This makes more sense than truncating an equal percent
    # of tokens from each, since if one sequence is very short then each token
    # that's truncated likely contains more information than a longer sequence.
    while True:
        total_length = len(tokens_a) + len(tokens_b)
        if total_length <= max_length:
            break
        if len(tokens_a) > len(tokens_b):
            tokens_a.pop()
        else:
            tokens_b.pop()

def convert_examples_to_features(
    examples, max_seq_length, tokenizer, print_examples=False
):
    """
    Loads a data file into a list of InputBatch objects
    :param examples:
    :param max_seq_length:
    :param tokenizer:
    :param print_examples:
    :return: a list of InputBatch objects
    """

    features = []
    for (ex_index, example) in enumerate(examples):
        tokens_a = tokenizer.tokenize(example.text_a)

        tokens_b = None
        if example.text_b:
            tokens_b = tokenizer.tokenize(example.text_b)
            # Modifies `tokens_a` and `tokens_b` in place so that the total
            # length is less than the specified length.
            # Account for [CLS], [SEP], [SEP] with "- 3"
            _truncate_seq_pair(tokens_a, tokens_b, max_seq_length - 3)
        else:
            # Account for [CLS] and [SEP] with "- 2"
            if len(tokens_a) > max_seq_length - 2:
                tokens_a = tokens_a[: (max_seq_length - 2)]

        # The convention in BERT is:
        # (a) For sequence pairs:
        #  tokens:   [CLS] is this jack ##son ##ville ? [SEP] no it is not . [SEP]
        #  type_ids: 0   0  0    0    0     0       0 0    1  1  1  1   1 1
        # (b) For single sequences:
        #  tokens:   [CLS] the dog is hairy . [SEP]
        #  type_ids: 0   0   0   0  0     0 0
        #
        # Where "type_ids" are used to indicate whether this is the first
        # sequence or the second sequence. The embedding vectors for `type=0` and
        # `type=1` were learned during pre-training and are added to the wordpiece
        # embedding vector (and position vector). This is not *strictly* necessary
        # since the [SEP] token unambigiously separates the sequences, but it makes
        # it easier for the model to learn the concept of sequences.
        #
        # For classification tasks, the first vector (corresponding to [CLS]) is
        # used as as the "sentence vector". Note that this only makes sense because
        # the entire model is fine-tuned.
        tokens = ["[CLS]"] + tokens_a + ["[SEP]"]
        segment_ids = [0] * len(tokens)

        if tokens_b:
            tokens += tokens_b + ["[SEP]"]
            segment_ids += [1] * (len(tokens_b) + 1)

        input_ids = tokenizer.convert_tokens_to_ids(tokens)

        # The mask has 1 for real tokens and 0 for padding tokens. Only real
        # tokens are attended to.
        input_mask = [1] * len(input_ids)

        # Zero-pad up to the sequence length.
        padding = [0] * (max_seq_length - len(input_ids))
        input_ids += padding
        input_mask += padding
        segment_ids += padding

        assert len(input_ids) == max_seq_length
        assert len(input_mask) == max_seq_length
        assert len(segment_ids) == max_seq_length

        label_id = [float(x) for x in example.label]

        if print_examples and ex_index < 5:
            print("tokens: %s" % " ".join([str(x) for x in tokens]))
            print("input_ids: %s" % " ".join([str(x) for x in input_ids]))
            print("input_mask: %s" % " ".join([str(x) for x in input_mask]))
            print("segment_ids: %s" % " ".join([str(x) for x in segment_ids]))
            print("label: %s" % example.label)

        features.append(
            InputFeatures(
                input_ids=input_ids,
                input_mask=input_mask,
                segment_ids=segment_ids,
                label_id=label_id,
            )
        )
    return features


def get_train_loader(train_features, batch_size):
    unpadded_input_ids = [f.input_ids for f in train_features]
    unpadded_input_mask = [f.input_mask for f in train_features]
    unpadded_segment_ids = [f.segment_ids for f in train_features]

    padded_input_ids = torch.tensor(unpadded_input_ids, dtype=torch.long)
    padded_input_mask = torch.tensor(unpadded_input_mask, dtype=torch.long)
    padded_segment_ids = torch.tensor(unpadded_segment_ids, dtype=torch.long)
    label_ids = torch.tensor([f.label_id for f in train_features], dtype=torch.long)

    train_data = TensorDataset(
        padded_input_ids, padded_input_mask, padded_segment_ids, label_ids
    )
    train_sampler = RandomSampler(train_data)
    train_dataloader = DataLoader(
        train_data, sampler=train_sampler, batch_size=batch_size
    )
    return train_dataloader


def get_test_loader(test_features, batch_size):
    unpadded_input_ids = [f.input_ids for f in test_features]
    unpadded_input_mask = [f.input_mask for f in test_features]
    unpadded_segment_ids = [f.segment_ids for f in test_features]

    padded_input_ids = torch.tensor(unpadded_input_ids, dtype=torch.long)
    padded_input_mask = torch.tensor(unpadded_input_mask, dtype=torch.long)
    padded_segment_ids = torch.tensor(unpadded_segment_ids, dtype=torch.long)

    test_data = TensorDataset(padded_input_ids, padded_input_mask, padded_segment_ids)

    test_sampler = RandomSampler(test_data)
    test_dataloader = DataLoader(
        test_data, shuffle=False, sampler=test_sampler, batch_size=batch_size
    )
    return test_dataloader


def convert_examples_to_hierarchical_features(
    examples, max_seq_length, tokenizer, print_examples=False
):
    """
    Loads a data file into a list of InputBatch objects
    :param examples:
    :param max_seq_length:
    :param tokenizer:
    :param print_examples:
    :return: a list of InputBatch objects
    """

    features = []
    for (ex_index, example) in enumerate(examples):
        tokens_a = [tokenizer.tokenize(line) for line in sent_tokenize(example.text_a)]
        tokens_b = None

        if example.text_b:
            tokens_b = [
                tokenizer.tokenize(line) for line in sent_tokenize(example.text_b)
            ]
            # Modifies `tokens_a` and `tokens_b` in place so that the total length is less than the specified length
            # Account for [CLS], [SEP], [SEP]
            _truncate_seq_pair(tokens_a, tokens_b, max_seq_length - 3)
        else:
            # Account for [CLS] and [SEP]
            for i0 in range(len(tokens_a)):
                if len(tokens_a[i0]) > max_seq_length - 2:
                    tokens_a[i0] = tokens_a[i0][: (max_seq_length - 2)]

        tokens = [["[CLS]"] + line + ["[SEP]"] for line in tokens_a]
        segment_ids = [[0] * len(line) for line in tokens]

        if tokens_b:
            tokens += tokens_b + ["[SEP]"]
            segment_ids += [1] * (len(tokens_b) + 1)

        input_ids = list()
        for line in tokens:
            input_ids.append(tokenizer.convert_tokens_to_ids(line))

        # Input mask has 1 for real tokens and 0 for padding tokens
        input_mask = [[1] * len(line_ids) for line_ids in input_ids]

        # Zero-pad up to the sequence length.
        padding = [[0] * (max_seq_length - len(line_ids)) for line_ids in input_ids]
        for i0 in range(len(input_ids)):
            input_ids[i0] += padding[i0]
            input_mask[i0] += padding[i0]
            segment_ids[i0] += padding[i0]

        label_id = [float(x) for x in example.label]

        if print_examples and ex_index < 5:
            print("tokens: %s" % " ".join([str(x) for x in tokens]))
            print("input_ids: %s" % " ".join([str(x) for x in input_ids]))
            print("input_mask: %s" % " ".join([str(x) for x in input_mask]))
            print("segment_ids: %s" % " ".join([str(x) for x in segment_ids]))
            print("label: %s" % example.label)

        features.append(
            InputFeatures(
                input_ids=input_ids,
                input_mask=input_mask,
                segment_ids=segment_ids,
                label_id=label_id,
            )
        )
    return features


def create_examples_from_df(df):
    examples = []
    for idx, row in df.iterrows():
        guid = idx
        text_a = row["docs"]
        if type(text_a) == float:
            print(row)
        if "labels" in df.columns:
            label = row["labels"]
        else:
            label = None
        examples.append(
            InputExample(guid=guid, text_a=text_a, text_b=None, label=label)
        )
    return examples
