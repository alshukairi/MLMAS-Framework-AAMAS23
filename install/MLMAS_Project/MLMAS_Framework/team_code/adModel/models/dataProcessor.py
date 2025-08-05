import os
import pandas as pd
import numpy as np
import random
from sklearn.preprocessing import StandardScaler

class dataProcessor:
    def __init__(self, root_dir, output_dir, mask_node_num):
        self.root_dir = root_dir
        self.output_dir = output_dir
        self.mask_node_num = mask_node_num
        self.seed = 42
        self.start_idx = 1
        self.edge_scaler = None
        self.node_scaler = None

    def load_data(self):
        self.edges_df = pd.read_csv(os.path.join(self.root_dir, 'all_edges.csv'))
        self.e_feat_df = pd.read_csv(os.path.join(self.root_dir, 'edge_features.csv'))
        self.n_feat_df = pd.read_csv(os.path.join(self.root_dir, 'node_features.csv'))

    def process(self):
        # Standardize edge features
        edge_numeric = self.e_feat_df[['rel_dis', 'vx', 'vy', 'yaw']].copy()
        edge_scaled_features = self.edge_scaler.fit_transform(edge_numeric)
        self.e_feat_df[['rel_dis', 'vx', 'vy', 'yaw']] = edge_scaled_features

        # Standardize node features
        node_numeric = self.n_feat_df[['w', 'h', 'l']].copy()
        node_scaled_features = self.node_scaler.fit_transform(node_numeric)
        self.n_feat_df[['w', 'h', 'l']] = node_scaled_features

        # Split nodes

        self.valid_edge_feats = self.e_feat_df.sort_values(by='time').copy()
        unique_times = np.sort(self.valid_edge_feats['time'].unique())
        ts_cutoffs = np.quantile(unique_times, [0.8, 0.9])

        # print('ts_cutoffs:', ts_cutoffs)
        self.train_df_raw = self.valid_edge_feats[self.valid_edge_feats['time'] <= ts_cutoffs[0]]
        self.val_df_raw = self.valid_edge_feats[self.valid_edge_feats['time'] > ts_cutoffs[0]]

    def build_edge_event_table_from_df(self, df_raw, start_idx, type):
        rows = []
        features = []
        feature_idx = start_idx
        feat = None
        for _, row in df_raw.iterrows():
            if type == 'train':
                feat = [row['rel_dis'], row['vx'], row['vy'], row['yaw']]
            elif type == 'val':
                feat = [0, 0, 0, 0]
            features.append(feat)
            rows.append({
                'u': row['src'],
                'i': row['dst'],
                'ts': row['time'],
                'ego': row['ego'],
                'idx': feature_idx
            })
            feature_idx += 1

        return pd.DataFrame(rows), np.array(features), feature_idx

    def build_datasets(self):
        self.train_df, self.train_feat, train_end_idx = self.build_edge_event_table_from_df(self.train_df_raw, self.start_idx, 'train')
        self.val_df, self.val_feat, val_end_idx = self.build_edge_event_table_from_df(self.val_df_raw, train_end_idx, 'val')

        self.finder_df = pd.concat([self.train_df, self.val_df], ignore_index=True)


        self.all_edge_feat = np.vstack([
            np.zeros((1, self.train_feat.shape[1])),
            self.train_feat,
            self.val_feat,

        ])

        n_feat_df_sorted = self.n_feat_df.sort_values(by='global_id')
        self.n_feat_matrix = n_feat_df_sorted.drop(columns=['global_id', 'agent_id','scenario_id']).to_numpy()
        self.n_feat_matrix = np.vstack([np.zeros((1, self.n_feat_matrix.shape[1])), self.n_feat_matrix])

    def save_all(self):
        os.makedirs(self.output_dir, exist_ok=True)
        pd.DataFrame(self.train_df).to_csv(os.path.join(self.output_dir, "ml_train.csv"), index=False)
        pd.DataFrame(self.val_df).to_csv(os.path.join(self.output_dir, "ml_val.csv"), index=False)

        pd.DataFrame(self.finder_df).to_csv(os.path.join(self.output_dir, "finder_df.csv"), index=False)


        np.save(os.path.join(self.output_dir, "e_feat.npy"), self.all_edge_feat)
        np.save(os.path.join(self.output_dir, "n_feat.npy"), self.n_feat_matrix)


    def run(self):
        self.edge_scaler = StandardScaler()
        self.node_scaler = StandardScaler()
        self.load_data()
        self.process()
        self.build_datasets()
        self.save_all()
