import numpy as np

class neighborFinder:
    def __init__(self, edge_df,ngh_proportion):
        self.node_to_neighbors = {}
        self.build_index(edge_df)
        self.ngh_proportion = ngh_proportion
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

            # 改这里：用 src 自己替换邻居 ID
            # ngh_nodes = [src for _ in valid] + [0] * pad_len
            ngh_nodes = [x[0] for x in valid] + [0] * pad_len
            eidxs = [x[1] for x in valid] + [0] * pad_len
            ts_list = [x[2] for x in valid] + [0] * pad_len

            out_ngh_nodes.append(ngh_nodes)
            out_eidx.append(eidxs)
            out_ts.append(ts_list)

        return (
            np.array(out_ngh_nodes),
            np.array(out_eidx),
            np.array(out_ts)
        )
