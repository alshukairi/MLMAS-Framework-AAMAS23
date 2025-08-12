import numpy as np

class neighborFinder:
    def __init__(self, edge_df, e_feat, ngh_proportion):
        self.node_to_neighbors = {}
        self.build_index(edge_df)
        self.ngh_proportion = ngh_proportion

        # 保存边特征（numpy 或 torch 都行，这里用 numpy）
        self.e_feat = e_feat  # [num_edges, De]

    def build_index(self, df):
        for row in df.itertuples(index=False):
            src, dst, ts, eidx = row.u, row.i, row.ts, row.idx
            if src not in self.node_to_neighbors:
                self.node_to_neighbors[src] = []
            self.node_to_neighbors[src].append((dst, eidx, ts))

        for node in self.node_to_neighbors:
            self.node_to_neighbors[node].sort(key=lambda x: x[2])

    def get_temporal_neighbor(self, src_idx_l, cut_time_l, num_neighbors=20):
        out_ngh_nodes = []
        out_eidx = []
        out_ts = []
        out_rel_dis_diff = []

        for src, cut_t in zip(src_idx_l, cut_time_l):
            neighbors = self.node_to_neighbors.get(src, [])
            if self.ngh_proportion == 1.0:
                threshold = cut_t
                valid = [(dst, eidx, ts) for dst, eidx, ts in neighbors if ts < threshold]
            else:
                threshold = cut_t * self.ngh_proportion
                valid = [(dst, eidx, ts) for dst, eidx, ts in neighbors if ts <= threshold]

            valid = valid[-num_neighbors:]
            pad_len = num_neighbors - len(valid)

            ngh_nodes = [x[0] for x in valid] + [0] * pad_len
            eidxs = [x[1] for x in valid] + [0] * pad_len
            ts_list = [x[2] for x in valid] + [0] * pad_len

            # 从 e_feat 里取 rel_dis
            rel_dis_list = [self.e_feat[eidx, 0] if eidx != 0 else 0.0 for eidx in eidxs]  # 第0列是 rel_dis

            # 相邻差分
            rel_dis_diff = []
            for i in range(len(rel_dis_list)):
                if i == 0:
                    rel_dis_diff.append(0.0)
                else:
                    rel_dis_diff.append(rel_dis_list[i] - rel_dis_list[i - 1])

            out_ngh_nodes.append(ngh_nodes)
            out_eidx.append(eidxs)
            out_ts.append(ts_list)
            out_rel_dis_diff.append(rel_dis_diff)

        return (
            np.array(out_ngh_nodes),
            np.array(out_eidx),
            np.array(out_ts),
            np.array(out_rel_dis_diff)
        )