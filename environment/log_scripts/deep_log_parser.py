import pandas as pd
import glob
import os
import ast

def remove_outliers(latencies):
    if len(latencies) == 0:
        return latencies
    Q1 = pd.Series(latencies).quantile(0.25)
    Q3 = pd.Series(latencies).quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return [latency for latency in latencies if lower_bound <= latency <= upper_bound]

def compute_mean(row, list_col):
    y_list = row[list_col]

    if not isinstance(y_list, list):
        y_list = [] if pd.isna(y_list) else [y_list]

    return sum(y_list) / len(y_list)

def mean_scalar_list(df, scalar_col, list_col, result_col):
    def compute_mean_with_scalar(row):
        x = row[scalar_col]
        y_list = row[list_col]

        if not isinstance(y_list, list):
            y_list = [] if pd.isna(y_list) else [y_list]
        
        # Combine values
        values = [x] + y_list if not pd.isna(x) else y_list
        return sum(values) / len(values) if values else None

    df[result_col] = df.apply(compute_mean_with_scalar, axis=1)
    return df

# Calculate latency from timestamps
def calculate_latency(row):
    epoch_timestamp = row['epoch_generating_timestamp']
    if pd.isna(epoch_timestamp) or not isinstance(row['other_timestamps'], list):
        return []
    
    else:
        return [ts - epoch_timestamp for ts in row['other_timestamps'] if pd.notna(ts)]

def calculate_latency_statistics(latencies):
    if len(latencies) == 0:
        return pd.Series([None, None], index=['mean_latency', 'max_latency'])
    return pd.Series([pd.Series(latencies).mean(), pd.Series(latencies).max()],
                     index=['mean_latency', 'max_latency'])


pd.options.display.max_columns = None
log_directory = '../client/logs'

options = ["outliers", "ignore_zeros"]
log_files = glob.glob(os.path.join(log_directory, '*.txt'))

data_frames_commit = []
data_frames_process = []

def read_log_file(file):
    data_commit = []
    data_process = []
    with open(file, 'r') as f:
        for line in f:
            try: 
                parts = line.split()

                if len(parts) < 5:
                    continue
                # 5th element determines the operation
                operation = parts[4]

                if operation == "DeepCommit":
                    group, epoch, num_users, user_id, operation, _size, _bars, total_commit, validation, apply_proposals, tree, path, tree_hash, parent_hash, encrypt_path, sign, schedule, welcome, _bars_2, storage_commit, encrypt, _bars_3, export, _bars_4, total_merge, merge, storage_merge, timestamp, elapsed = parts
                    data_commit.append([group, int(epoch), int(num_users), user_id, operation, int(total_commit), int(validation), int(apply_proposals), int(tree), int(path), int(tree_hash), int(parent_hash), int(encrypt_path), int(sign), int(schedule), int(welcome), int(storage_commit), int(encrypt), int(export), int(total_merge), int(merge), int(storage_merge), int(timestamp), int(elapsed)])

                elif operation == "DeepProcess":
                    group, epoch, num_users, user_id, operation, _target_user_id, _bars, total_process, decrypt, verify, validation, apply_proposals, tree, path, tree_hash, parent_hash, decrypt_path, schedule, _bars_2,  total_merge, merge, storage, timestamp, elapsed = parts
                    #group, epoch, num_users, user_id, operation, total_process, decrypt, verify, validation, apply_proposals, path, schedule, _bars, total_merge, merge, storage, timestamp, elapsed = parts
                    data_process.append([group, int(epoch), int(num_users), user_id, operation, int(total_process), int(decrypt), int(verify), int(validation), int(apply_proposals), int(tree), int(path), int(tree_hash), int(parent_hash), int(decrypt_path), int(schedule), int(total_merge), int(merge), int(storage), int(timestamp), int(elapsed)])
            except ValueError as e:
                print(line, e)
    # create dataframe with all lines
    df_commit = pd.DataFrame(data_commit, columns=["group", "epoch", "num_users", "user_id", "operation", "total_commit", "validation", "apply_proposals", "tree", "path", "tree_hash", "parent_hash", "encrypt_path", "sign", "schedule", "welcome", "storage_commit", "encrypt", "export", "total_merge", "merge", "storage_merge", "timestamp", "elapsed"])
    # create dataframe with all lines
    df_process = pd.DataFrame(data_process, columns=["group", "epoch", "num_users", "user_id", "operation", "total_process", "decrypt", "verify", "validation", "apply_proposals", "tree", "path", "tree_hash", "parent_hash", "decrypt_path", "schedule", "total_merge", "merge", "storage", "timestamp", "elapsed"])
    
    return df_commit, df_process

# Parse all log files into a dataframe
for file in log_files:
    df_commit, df_process = read_log_file(file)
    data_frames_commit.append(df_commit)
    data_frames_process.append(df_process)

# Concatenate all dataframes
all_commit_df = pd.concat(data_frames_commit, ignore_index=True)
all_process_df = pd.concat(data_frames_process, ignore_index=True)

# Group logs by group and epoch and rename columns
# Should only be 1 "epoch_generating_event" for group and epoch
epoch_generating_events_grouped = all_commit_df.groupby(['group', 'epoch']).first().reset_index()

epoch_generating_events_grouped['gen_total'] = epoch_generating_events_grouped['total_commit'] + epoch_generating_events_grouped['export'] + epoch_generating_events_grouped['total_merge']
epoch_generating_events_grouped['gen_storage'] = epoch_generating_events_grouped['storage_commit'] + epoch_generating_events_grouped['storage_merge']
e = epoch_generating_events_grouped
epoch_generating_events_grouped['commit_other'] = e['gen_total'] - (e['validation'] + e['apply_proposals'] + e['tree'] + e['path'] + e['tree_hash'] + e['parent_hash'] + e['encrypt_path'] + e['sign'] + e['schedule'] + e['welcome'] + e['encrypt'] + e['export'] + e['gen_storage'] + e['merge']) 

epoch_generating_events_grouped.rename(columns={'timestamp': 'epoch_generating_timestamp'}, inplace=True)
epoch_generating_events_grouped.rename(columns={'validation': 'commit_validation'}, inplace=True)
epoch_generating_events_grouped.rename(columns={'apply_proposals': 'commit_apply_proposals'}, inplace=True)
epoch_generating_events_grouped.rename(columns={'tree': 'commit_tree'}, inplace=True)
epoch_generating_events_grouped.rename(columns={'path': 'commit_path'}, inplace=True)
epoch_generating_events_grouped.rename(columns={'tree_hash': 'commit_tree_hash'}, inplace=True)
epoch_generating_events_grouped.rename(columns={'parent_hash': 'commit_parent_hash'}, inplace=True)
epoch_generating_events_grouped.rename(columns={'encrypt_path': 'commit_encrypt_path'}, inplace=True)
epoch_generating_events_grouped.rename(columns={'sign': 'commit_sign'}, inplace=True)
epoch_generating_events_grouped.rename(columns={'schedule': 'commit_schedule'}, inplace=True)
epoch_generating_events_grouped.rename(columns={'welcome': 'commit_welcome'}, inplace=True)
epoch_generating_events_grouped.rename(columns={'encrypt': 'commit_encrypt'}, inplace=True)
epoch_generating_events_grouped.rename(columns={'export': 'commit_export'}, inplace=True)
epoch_generating_events_grouped.rename(columns={'merge': 'commit_merge'}, inplace=True)
epoch_generating_events_grouped.rename(columns={'elapsed': 'gen_elapsed_mean'}, inplace=True)

process_events_grouped = all_process_df.groupby(['group', 'epoch']).agg({
    'timestamp': list,
    'elapsed': 'mean',
    'total_process': 'mean',
    'decrypt': 'mean',
    'verify': 'mean',
    'validation': 'mean',
    'apply_proposals': 'mean',
    'tree': 'mean',
    'path': 'mean',
    'tree_hash': 'mean',
    'parent_hash': 'mean',
    'decrypt_path': 'mean',
    'schedule': 'mean',
    'total_merge': 'mean',
    'merge': 'mean',
    'storage': 'mean',
}).reset_index()

process_events_grouped['process_total'] = process_events_grouped['total_process'] + process_events_grouped['total_merge']
p = process_events_grouped
process_events_grouped['process_other'] = p['process_total'] - (p['decrypt'] + p['verify'] + p['validation'] + p['apply_proposals'] + p['tree'] + p['path'] + p['decrypt_path'] + p['schedule'] + p['merge'] + p['storage'])

process_events_grouped.rename(columns={'timestamp': 'other_timestamps'}, inplace=True)
process_events_grouped.rename(columns={'elapsed': 'processing_elapsed_mean'}, inplace=True)
process_events_grouped.rename(columns={'decrypt': 'process_decrypt'}, inplace=True)
process_events_grouped.rename(columns={'verify': 'process_verify'}, inplace=True)
process_events_grouped.rename(columns={'validation': 'process_validation'}, inplace=True)
process_events_grouped.rename(columns={'apply_proposals': 'process_apply_proposals'}, inplace=True)
process_events_grouped.rename(columns={'tree': 'process_tree'}, inplace=True)
process_events_grouped.rename(columns={'path': 'process_path'}, inplace=True)
process_events_grouped.rename(columns={'tree_hash': 'process_tree_hash'}, inplace=True)
process_events_grouped.rename(columns={'parent_hash': 'process_parent_hash'}, inplace=True)
process_events_grouped.rename(columns={'decrypt_path': 'process_decrypt_path'}, inplace=True)
process_events_grouped.rename(columns={'schedule': 'process_schedule'}, inplace=True)
process_events_grouped.rename(columns={'merge': 'process_merge'}, inplace=True)
process_events_grouped.rename(columns={'storage': 'process_storage'}, inplace=True)


# Combine all dataframes
grouped_logs = pd.merge(epoch_generating_events_grouped, process_events_grouped, on=['group', 'epoch'], how='left')

grouped_logs['num_users'] = grouped_logs['num_users'].fillna(1).astype(int)
grouped_logs['latency'] = grouped_logs.apply(calculate_latency, axis=1)

if "outliers" in options:
    grouped_logs['latency'] = grouped_logs['latency'].apply(remove_outliers)
# Add mean an max latency columns in seconds
stats = grouped_logs['latency'].apply(calculate_latency_statistics)
grouped_logs = pd.concat([grouped_logs, stats], axis=1)
grouped_logs['mean_latency'] = pd.to_numeric(grouped_logs['mean_latency'], errors='coerce') / 1e3
grouped_logs['max_latency'] = pd.to_numeric(grouped_logs['max_latency'], errors='coerce') / 1e3

# order dataframe
grouped_logs = grouped_logs.sort_values(by=['group', 'epoch']).reset_index(drop=True)

# print and save`
print(grouped_logs)
grouped_logs.to_csv('deep_grouped_logs.csv', index=False)
