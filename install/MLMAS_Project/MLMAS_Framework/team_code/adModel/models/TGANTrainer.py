import os
import math
import numpy as np
import pandas as pd
import torch
from adModel.models.neighborFinder import neighborFinder
from adModel.models.tgan import TGAN

class TGANTrainer:
    def __init__(self,
                 data_dir,
                 output_dir,
                 batch_size=64):
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.batch_size = batch_size


        self.device = self._get_device()
        self._prepare_dirs()
        self._load_data()
        self._init_model()

    def _get_device(self):
        if torch.cuda.is_available():
            print("✅ Using GPU")
            return torch.device("cuda")
        elif torch.backends.mps.is_available():
            print("✅ Using MPS")
            return torch.device("mps")
        else:
            print("✅ Using CPU")
            return torch.device("cpu")

    def _prepare_dirs(self):
        self.log_dir = os.path.join(self.output_dir, "saved_log")
        self.ckpt_dir = os.path.join(self.output_dir, "saved_checkpoints")
        self.model_dir = os.path.join(self.output_dir, "saved_models")
        for d in [self.output_dir, self.log_dir, self.ckpt_dir, self.model_dir]:
            os.makedirs(d, exist_ok=True)

    def _load_data(self):
        self.n_feat = np.load(os.path.join(self.data_dir, "n_feat.npy"))
        self.e_feat = np.load(os.path.join(self.data_dir, "e_feat.npy"))

        val_df = pd.read_csv(os.path.join(self.data_dir, "ml_val.csv"))
        self.finder_df = pd.read_csv(os.path.join(self.data_dir, "finder_df.csv"))

        pos_val_df = val_df[val_df['ego'] == 1].copy()
        # Validation subset
        self.val_src = pos_val_df.u.values
        self.val_dst = pos_val_df.i.values
        self.val_ts = pos_val_df.ts.values
        # self.val_idx = pos_val_df.idx.values


    def _init_model(self):

        self.full_ngh_finder = neighborFinder(self.finder_df, ngh_proportion=1)

        self.tgan = TGAN(
            ngh_finder=self.full_ngh_finder,
            n_feat=self.n_feat,
            e_feat=self.e_feat,
            num_layers=2,
            agg_method='attn',
            use_time='time',
        ).to(self.device)

        weight_path = "./weights/tgan_final.pth"
        if not os.path.exists(weight_path):
            raise FileNotFoundError(f"Missing model weights at {weight_path}")
        state_dict = torch.load(weight_path, map_location=self.device)

        self.tgan.load_state_dict(state_dict)


        self.optimizer = torch.optim.Adam(self.tgan.parameters(), lr=0.001)
        self.criterion = torch.nn.BCEWithLogitsLoss()

    def eval(self):

        self.tgan.ngh_finder = self.full_ngh_finder

        acc, ap, f1, auc = self.top_k(
            self.tgan,
            self.val_src,
            self.val_dst,
            self.val_ts,
            self.batch_size,
            num_neighbors=20,
            top_k = 3
        )

    def top_k(self, tgan, src, dst, ts, batch_size, num_neighbors, top_k):
        all_scores = []
        all_dst = []

        with torch.no_grad():
            tgan.eval()
            num_test_instance = len(src)
            num_test_batch = math.ceil(num_test_instance / batch_size)

            for k in range(num_test_batch):
                s_idx = k * batch_size
                e_idx = min(num_test_instance, s_idx + batch_size)
                src_cut = src[s_idx:e_idx]
                dst_cut = dst[s_idx:e_idx]
                ts_cut = ts[s_idx:e_idx]

                logits = tgan.forward(src_cut, dst_cut, ts_cut, num_neighbors)
                scores = logits.sigmoid().cpu().numpy().flatten()

                all_scores.extend(scores)
                all_dst.extend(dst_cut)

        # 全部拼接后取 top_k
        top_k_indices = np.argsort(-np.array(all_scores))[:top_k]
        top_k_dst = [all_dst[i] for i in top_k_indices]
        top_k_scores = [all_scores[i] for i in top_k_indices]

        return list(zip(top_k_dst, top_k_scores))


