import os
import math
import numpy as np
import pandas as pd
import torch
from adModel.models.neighborFinder import neighborFinder
from adModel.models.tgan import TGAN
from leaderboard.leaderboard_evaluator import LeaderboardEvaluator

class TGANTrainer:
    def __init__(self, data_dir, output_dir, batch_size):
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.batch_size = batch_size

        self.device = self._get_device()
        self._prepare_dirs()
        self._load_data()
        self._init_model()

    def _get_device(self):
        if torch.cuda.is_available():
            # print("Using GPU")
            return torch.device("cuda")
        elif torch.backends.mps.is_available():
            # print("Using MPS")
            return torch.device("mps")
        else:
            # print("Using CPU")
            return torch.device("cpu")

    def _prepare_dirs(self):

        os.makedirs(self.output_dir, exist_ok=True)

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



    def _init_model(self):

        self.full_ngh_finder = neighborFinder(self.finder_df, ngh_proportion=1)

        self.tgan = TGAN(
            ngh_finder=self.full_ngh_finder,
            n_feat=self.n_feat,
            e_feat=self.e_feat,
            num_layers=2,
            agg_method='attn',
            use_time='time',
            dev = self.device
        ).to(self.device)

        weight_path = "MLMAS_Framework/team_code/accidentDetection/weights/tgan_final.pth"
        if not os.path.exists(weight_path):
            raise FileNotFoundError(f"Missing model weights at {weight_path}")

        state_dict = torch.load(weight_path, map_location=self.device)
        self.tgan.load_state_dict(state_dict,strict=False)


        self.optimizer = torch.optim.Adam(self.tgan.parameters(), lr=0.001)
        self.criterion = torch.nn.BCEWithLogitsLoss()

    def eval(self):

        self.tgan.ngh_finder = self.full_ngh_finder
        # print(f"val_src: {self.val_src}")
        # print(f"val_dst: {self.val_dst}")
        # print(f"val_ts: {self.val_ts}")

        df = self.predict_all_dst_for_each_src(self.tgan,top_k=5)


    def predict_all_dst_for_each_src(self,tgan, top_k=3, num_neighbors=20):
        tgan.eval()

        all_node_ids = np.unique(
            np.concatenate([self.finder_df["u"].values, self.finder_df["i"].values])
        )

        results = []

        with torch.no_grad():
            for src, ts in zip(self.val_src, self.val_ts):
                dst_candidates = [n for n in all_node_ids if n != src]
                dst_array = np.array(dst_candidates)
                src_array = np.array([src] * len(dst_array))
                ts_array = np.array([ts] * len(dst_array))

                logits = tgan.forward(src_array, dst_array, ts_array, num_neighbors)
                logits_np = logits.cpu().numpy().flatten()
                scores_np = torch.sigmoid(logits).cpu().numpy().flatten()

                # 取 top-k dst
                top_k_indices = np.argsort(-scores_np)

                for i in top_k_indices:
                    results.append({
                        "src": int(src_array[i]),
                        "dst": int(dst_array[i]),
                        "score": float(scores_np[i]),
                        "logits": float(logits_np[i]),
                        "ts": int(ts),
                    })
                max_inx = top_k_indices[0]
                max_score = float(scores_np[max_inx])
                if max_score > 0.7:
                    c_src = int(dst_array[max_inx])
                    c_dst = int(dst_array[max_inx])
                    c_ts = int(ts)
                    print(f"Collision : src: {c_src}, dst: {c_dst}, ts: {c_ts}")

        df = pd.DataFrame(results)
        df.to_csv(os.path.join(self.output_dir, "topk_dst_predictions.csv"), index=False)
        # print("Top-k prediction results saved to:", self.output_dir)
        # print(df.head())

        return df

