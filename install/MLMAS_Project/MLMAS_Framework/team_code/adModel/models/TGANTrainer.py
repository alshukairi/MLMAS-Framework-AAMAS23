import os
import math
import numpy as np
import pandas as pd
import torch
from adModel.models.neighborFinder import neighborFinder
from adModel.models.randEdgeSampler import RandEdgeSampler
from adModel.models.tgan import TGAN

os.environ['CUDA_LAUNCH_BLOCKING'] = '1'

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
            return torch.device("cuda")
        elif torch.backends.mps.is_available():
            return torch.device("mps")
        else:
            return torch.device("cpu")

    def _prepare_dirs(self):

        os.makedirs(self.output_dir, exist_ok=True)

    def _load_data(self):
        self.n_feat = np.load(os.path.join(self.data_dir, "n_feat.npy"))
        self.e_feat = np.load(os.path.join(self.data_dir, "e_feat.npy"))


        val_df = pd.read_csv(os.path.join(self.data_dir, "ml_val.csv"))

        self.finder_df = pd.read_csv(os.path.join(self.data_dir, "finder_df.csv"))

        pos_val_df = val_df[(val_df['ego'] == 1)].copy()
        self.pos_val_src = pos_val_df.u.values
        self.pos_val_dst = pos_val_df.i.values
        self.pos_val_ts = pos_val_df.ts.values



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

        weight_path = "MLMAS_Framework/team_code/adModel/weights/tgan_final.pth"
        if not os.path.exists(weight_path):
            raise FileNotFoundError(f"Missing model weights at {weight_path}")

        state_dict = torch.load(weight_path, map_location=self.device)
        self.tgan.load_state_dict(state_dict,strict=False)


    def eval(self):
        self.tgan.ngh_finder = self.full_ngh_finder

        df = self.eval_one_epoch(
            self.tgan,
            self.pos_val_src, self.pos_val_dst, self.pos_val_ts,
            batch_size = 8, num_neighbors =20
        )

        return df

    def _stat(self,np_arr, name):
        arr = np.asarray(np_arr)
        print(f"[{name}] shape={arr.shape} dtype={arr.dtype} "
              f"nan={np.isnan(arr).any()} inf={np.isinf(arr).any()}")

    def eval_one_epoch(self, tgan, src, dst, ts, batch_size, num_neighbors):
        results = []
        with torch.no_grad():
            tgan.eval()

            num_instance = len(src)
            num_batch = (num_instance + batch_size - 1) // batch_size
            for k in range(num_batch):
                s_idx = k * batch_size
                e_idx = min(s_idx + batch_size, num_instance)

                src_l_cut = src[s_idx:e_idx]
                dst_l_cut = dst[s_idx:e_idx]
                ts_l_cut = ts[s_idx:e_idx]

                logits = tgan.forward(src_l_cut, dst_l_cut, ts_l_cut, num_neighbors)

                pos_prob = torch.sigmoid(logits).detach().cpu().numpy()

                for i in range(len(pos_prob)):
                    results.append({
                        "src": int(src_l_cut[i]),
                        "dst": int(dst_l_cut[i]),
                        "score": float(pos_prob[i]),
                        "logits": float(logits[i].item()),
                        "ts": int(ts_l_cut[i]),
                    })

        df = pd.DataFrame(results)


        return df


