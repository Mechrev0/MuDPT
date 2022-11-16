import os
import pickle

from dassl.data.datasets import DATASET_REGISTRY, DatasetBase, Datum
from dassl.utils import listdir_nohidden
from datasets.imagenet import ImageNet


@DATASET_REGISTRY.register()
class ImageNetV2(DatasetBase):

    dataset_dir = "imagenetv2"

    def __init__(self, cfg):
        root = os.path.abspath(os.path.expanduser(cfg.DATASET.ROOT))
        self.dataset_dir = os.path.join(root, self.dataset_dir)
        self.image_dir = os.path.join(self.dataset_dir, "imagenetv2-matched-frequency-format-val")
        self.preprocessed_dir = os.path.join(self.dataset_dir, "preprocessed.pkl")

        text_file = os.path.join(self.dataset_dir, "classnames.txt")
        classnames = ImageNet.read_classnames(text_file)

        if os.path.exists(self.preprocessed_dir):
            print(f"Loading preprocessed data from {self.preprocessed_dir}")
            with open(self.preprocessed_dir, "rb") as f:
                preprocessed = pickle.load(f)
                data = preprocessed["data"]
        else:
            data = self.read_data(classnames)
            preprocessed = {"data": data}
            print(f"Saving preprocessed data to {self.preprocessed_dir}")
            with open(self.preprocessed_dir, "wb") as file:
                pickle.dump(preprocessed, file, protocol=pickle.HIGHEST_PROTOCOL)

        super().__init__(train_x=data, test=data)

    def read_data(self, classnames):
        image_dir = self.image_dir
        folders = list(classnames.keys())
        items = []
        for label in range(1000):
            class_dir = os.path.join(image_dir, str(label))
            imnames = listdir_nohidden(class_dir)
            folder = folders[label]
            classname = classnames[folder]
            for imname in imnames:
                impath = os.path.join(class_dir, imname)
                item = Datum(impath=impath, label=label, classname=classname)
                items.append(item)

        return items