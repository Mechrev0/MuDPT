import os
import math
import pickle
import random

from collections import defaultdict
from scipy.io import loadmat

from dassl.data.datasets import DATASET_REGISTRY, Datum, DatasetBase
from dassl.utils import mkdir_if_missing, read_json, write_json


@DATASET_REGISTRY.register()
class StanfordCars(DatasetBase):

    dataset_dir = "stanford_cars"

    def __init__(self, cfg):
        root = os.path.abspath(os.path.expanduser(cfg.DATASET.ROOT))
        self.dataset_dir = os.path.join(root, self.dataset_dir)
        self.preprocessed_dir = os.path.join(self.dataset_dir, "preprocessed.pkl")
        self.split_fewshot_dir = os.path.join(self.dataset_dir, "split_fewshot")
        mkdir_if_missing(self.split_fewshot_dir)

        if os.path.exists(self.preprocessed_dir):
            print(f"Loading preprocessed data from {self.preprocessed_dir}")
            with open(self.preprocessed_dir, "rb") as f:
                preprocessed = pickle.load(f)
                train, val, test = preprocessed["train"], preprocessed["val"], preprocessed["test"]
        else:
            train, val, test = self.read_data()
            preprocessed = {"train": train, "val": val, "test": test}
            print(f"Saving preprocessed data to {self.preprocessed_dir}")
            with open(self.preprocessed_dir, "wb") as file:
                pickle.dump(preprocessed, file, protocol=pickle.HIGHEST_PROTOCOL)

        num_shots = cfg.DATASET.NUM_SHOTS
        if num_shots >= 1:
            seed = cfg.SEED
            fewshot_preprocessed_dir = os.path.join(self.split_fewshot_dir, f"shot_{num_shots}-seed_{seed}.pkl")
            if os.path.exists(fewshot_preprocessed_dir):
                print(f"Loading few-shot data from {fewshot_preprocessed_dir}")
                with open(fewshot_preprocessed_dir, "rb") as file:
                    fewshot_preprocessed = pickle.load(file)
                    train = fewshot_preprocessed["train"]
                    val = fewshot_preprocessed["val"]
            else:
                train = self.generate_fewshot_dataset(train, num_shots=num_shots)
                val = self.generate_fewshot_dataset(val, num_shots=min(num_shots, 4))
                fewshot_preprocessed = {"train": train, "val": val}
                print(f"Saving few-shot data to {fewshot_preprocessed_dir}")
                with open(fewshot_preprocessed_dir, "wb") as file:
                    pickle.dump(fewshot_preprocessed, file, protocol=pickle.HIGHEST_PROTOCOL)

        subsample = cfg.DATASET.SUBSAMPLE_CLASSES
        train, val, test = self.subsample_classes(train, val, test, subsample=subsample)
        super().__init__(train_x=train, val=val, test=test)

    def read_data(self, p_val=0.2):
        def read(image_dir, annotation_file, meta_file):
            anno_file = loadmat(annotation_file)["annotations"][0]
            meta_file = loadmat(meta_file)["class_names"][0]
            items = []

            for i in range(len(anno_file)):
                imname = anno_file[i]["fname"][0]
                impath = os.path.join(self.dataset_dir, image_dir, imname)
                label = anno_file[i]["class"][0, 0]
                label = int(label) - 1  # convert to 0-based index
                classname = meta_file[label][0]
                names = classname.split(" ")
                year = names.pop(-1)
                names.insert(0, year)
                classname = " ".join(names)
                item = Datum(impath=impath, label=label, classname=classname)
                items.append(item)

            return items

        trainval_mat = os.path.join(self.dataset_dir, "devkit", "cars_train_annos.mat")
        test_mat = os.path.join(self.dataset_dir, "cars_test_annos_withlabels.mat")
        cars_meta = os.path.join(self.dataset_dir, "devkit", "cars_meta.mat")

        trainval = read("cars_train", trainval_mat, cars_meta)
        test = read("cars_test", test_mat, cars_meta)

        # split train and val set
        # 1. category data according class
        # 2. split
        p_trn = 1 - p_val
        print(f"Splitting trainval into {p_trn:.0%} train and {p_val:.0%} val")
        tracker = defaultdict(list)
        for idx, item in enumerate(trainval):
            label = item.label
            tracker[label].append(idx)

        train, val = [], []
        for label, idxs in tracker.items():
            n_val = round(len(idxs) * p_val)
            assert n_val > 0
            random.shuffle(idxs)
            for n, idx in enumerate(idxs):
                item = trainval[idx]
                if n < n_val:
                    val.append(item)
                else:
                    train.append(item)

        return train, val, test

    @staticmethod
    def subsample_classes(*args, subsample="all"):
        """Divide classes into two groups. The first group
        represents base classes while the second group represents
        new classes.

        Args:
            args: a list of datasets, e.g. train, val and test.
            subsample (str): what classes to subsample.
        """
        assert subsample in ["all", "base", "new"]

        if subsample == "all":
            return args

        dataset = args[0]
        labels = set()
        for item in dataset:
            labels.add(item.label)
        labels = list(labels)
        labels.sort()
        n = len(labels)
        # Divide classes into two halves
        m = math.ceil(n / 2)

        print(f"SUBSAMPLE {subsample.upper()} CLASSES!")
        if subsample == "base":
            selected = labels[:m]  # take the first half
        else:
            selected = labels[m:]  # take the second half
        relabeler = {y: y_new for y_new, y in enumerate(selected)}

        output = []
        for dataset in args:
            dataset_new = []
            for item in dataset:
                if item.label not in selected:
                    continue
                item_new = Datum(
                    impath=item.impath,
                    label=relabeler[item.label],
                    classname=item.classname
                )
                dataset_new.append(item_new)
            output.append(dataset_new)

        return output
