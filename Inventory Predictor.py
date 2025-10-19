import os
import random
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import streamlit as st

# ===========================
# 1. Parameters and Settings
# ===========================
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

DATA_CSV = "synthetic_inventory_2years.csv"
SEQ_LEN = 20
BATCH_SIZE = 16
EPOCHS = 150
LR = 1e-3
PATIENCE = 15
FUTURE_STEPS = 4

# ===========================
# 2. Data Preparation
# ===========================
df = pd.read_csv(DATA_CSV)

orgs = df["Organization"].unique().tolist()

# Helper to create sliding windows
def create_windows(series, seq_len):
    X, y = [], []
    for i in range(len(series) - seq_len):
        X.append(series[i:i + seq_len])
        y.append(series[i + seq_len])
    return np.array(X), np.array(y)

# ===========================
# 3. Dataset Class
# ===========================
class SeqDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)
    def __len__(self):
        return len(self.X)
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

# ===========================
# 4. Model Definitions
# ===========================
class Chomp1d(nn.Module):
    def __init__(self, chomp_size):
        super().__init__()
        self.chomp_size = chomp_size
    def forward(self, x):
        return x[:, :, :-self.chomp_size] if self.chomp_size else x

class TemporalBlock(nn.Module):
    def __init__(self, n_inputs, n_outputs, kernel_size, stride, dilation, padding, dropout):
        super().__init__()
        self.conv1 = nn.Conv1d(n_inputs, n_outputs, kernel_size, stride=stride,
                               padding=padding, dilation=dilation)
        self.chomp1 = Chomp1d(padding)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(dropout)
        self.conv2 = nn.Conv1d(n_outputs, n_outputs, kernel_size, stride=stride,
                               padding=padding, dilation=dilation)
        self.chomp2 = Chomp1d(padding)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(dropout)
        self.net = nn.Sequential(
            self.conv1, self.chomp1, self.relu1, self.dropout1,
            self.conv2, self.chomp2, self.relu2, self.dropout2
        )
        self.downsample = nn.Conv1d(n_inputs, n_outputs, 1) if n_inputs != n_outputs else None
        self.final_relu = nn.ReLU()
    def forward(self, x):
        res = x if self.downsample is None else self.downsample(x)
        return self.final_relu(self.net(x) + res)

class TCNModel(nn.Module):
    def __init__(self, input_size=1, output_size=1, num_channels=[64, 64, 64], kernel_size=3, dropout=0.1):
        super().__init__()
        layers = []
        for i in range(len(num_channels)):
            dilation = 2 ** i
            in_ch = input_size if i == 0 else num_channels[i - 1]
            out_ch = num_channels[i]
            layers.append(
                TemporalBlock(in_ch, out_ch, kernel_size, stride=1, dilation=dilation,
                              padding=(kernel_size - 1) * dilation, dropout=dropout)
            )
        self.network = nn.Sequential(*layers)
        self.fc = nn.Linear(num_channels[-1], output_size)
    def forward(self, x):
        x = x.unsqueeze(1)
        y = self.network(x)
        return self.fc(y[:, :, -1]).squeeze(-1)

# ===========================
# 5. Training Helpers
# ===========================
def train_model(model, train_loader, val_loader, epochs=EPOCHS, lr=LR, patience=PATIENCE):
    model = model.to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
    criterion = nn.MSELoss()
    best_val = float("inf")
    best_state = None
    no_improve = 0

    for epoch in range(epochs):
        model.train()
        tr_loss = []
        for xb, yb in train_loader:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
            tr_loss.append(loss.item())
        model.eval()
        val_loss = []
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(DEVICE), yb.to(DEVICE)
                val_loss.append(criterion(model(xb), yb).item())
        avg_val = np.mean(val_loss)
        scheduler.step(avg_val)
        if avg_val < best_val:
            best_val = avg_val
            best_state = model.state_dict()
            no_improve = 0
        else:
            no_improve += 1
        if no_improve >= patience:
            break
    model.load_state_dict(best_state)
    return model

# ===========================
# 6. Forecast per Item
# ===========================
def forecast_item(org_name, item_name):
    subset = df[(df["Organization"] == org_name) & (df["Item"] == item_name)].sort_values("Week")
    if subset.empty or len(subset) < SEQ_LEN:
        return None

    series = subset["Starting_Quantity"].values.astype(float)
    X_all, y_all = create_windows(series, SEQ_LEN)

    n = len(X_all)
    train, val = int(0.7 * n), int(0.85 * n)
    X_train, y_train = X_all[:train], y_all[:train]
    X_val, y_val = X_all[train:val], y_all[train:val]

    scaler_X = StandardScaler().fit(X_train.reshape(-1, 1))
    scaler_y = StandardScaler().fit(y_train.reshape(-1, 1))

    def scale_X(X): return scaler_X.transform(X.reshape(-1, 1)).reshape(X.shape)
    X_train_s, X_val_s = scale_X(X_train), scale_X(X_val)
    y_train_s = scaler_y.transform(y_train.reshape(-1, 1)).reshape(-1)
    y_val_s = scaler_y.transform(y_val.reshape(-1, 1)).reshape(-1)

    train_loader = DataLoader(SeqDataset(X_train_s, y_train_s), batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(SeqDataset(X_val_s, y_val_s), batch_size=BATCH_SIZE)

    model = TCNModel()
    model = train_model(model, train_loader, val_loader)

    # Forecast next FUTURE_STEPS
    seq = series[-SEQ_LEN:]
    seq_scaled = torch.tensor(scale_X(seq.reshape(1, -1)), dtype=torch.float32).to(DEVICE)
    future_preds = []
    future_weeks = np.arange(subset["Week"].max() + 1, subset["Week"].max() + FUTURE_STEPS + 1)
    with torch.no_grad():
        for _ in range(FUTURE_STEPS):
            next_scaled = model(seq_scaled).cpu().numpy()
            next_val = scaler_y.inverse_transform(next_scaled.reshape(-1, 1)).ravel()[0]
            future_preds.append(next_val)
            next_input = scaler_X.transform(np.array([[next_val]]))
            seq_scaled = torch.cat((seq_scaled[:, 1:], torch.tensor(next_input, dtype=torch.float32).to(DEVICE)), dim=1)

    table_df = pd.DataFrame({
        "Item": item_name,
        "Week": future_weeks,
        "Predicted Quantity": future_preds
    })
    # Add Should_Buy column
    mean_pred = np.mean(future_preds)
    table_df["Should_Buy"] = np.where(table_df["Predicted Quantity"] < mean_pred * 0.8, "✅ Yes", "❌ No")

    # For plotting
    hist_weeks = subset["Week"].values
    hist_series = subset["Starting_Quantity"].values

    return table_df, hist_weeks, hist_series

# ===========================
# 7. Streamlit UI
# ===========================
st.set_page_config(layout="wide", page_title="Inventory Forecasting Dashboard")
st.title("📊 Inventory Forecasting Dashboard (TCN Model)")
st.markdown("Forecast inventory for all food items in a selected organization.")

selected_org = st.selectbox("Select Organization:", orgs)

# Auto-generate forecasts if not already done
if "forecasts" not in st.session_state:
    st.session_state.forecasts = {}

if selected_org not in st.session_state.forecasts:
    st.info(f"Precomputing forecasts for {selected_org} — please wait...")
    all_results = {}
    for item in df[df["Organization"] == selected_org]["Item"].unique():
        result = forecast_item(selected_org, item)
        if result is not None:
            all_results[item] = result
    st.session_state.forecasts[selected_org] = all_results

combined_forecasts = st.session_state.forecasts[selected_org]

# ===========================
# Item selection and plot
# ===========================
if combined_forecasts:
    selected_item = st.selectbox("Select Item to Display:", list(combined_forecasts.keys()))
    table_df, hist_weeks, hist_series = combined_forecasts[selected_item]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(hist_weeks, hist_series, color="blue", marker="o")
    ax.scatter(table_df["Week"], table_df["Predicted Quantity"], color="red", marker="X", s=100)
    ax.set_xlabel("Week")
    ax.set_ylabel("Starting Quantity")
    ax.set_title(f"Inventory Forecast for {selected_item}")
    ax.grid(alpha=0.3)
    st.pyplot(fig)

    st.subheader(f"📋 Forecast Table for {selected_item} (Next {FUTURE_STEPS} Weeks)")
    st.dataframe(table_df)

# ===========================
# General "Items to Buy" Table
# ===========================
summary_list = []
for item, result in combined_forecasts.items():
    table_df, _, _ = result
    buy_df = table_df[table_df["Should_Buy"] == "✅ Yes"]
    summary_list.append(buy_df)

if summary_list:
    summary_df = pd.concat(summary_list, ignore_index=True)
    st.subheader("🛒 Items to Buy in the Next 4 Weeks")
    st.dataframe(summary_df[["Item", "Week", "Predicted Quantity", "Should_Buy"]])
else:
    st.info("No items need to be bought based on predictions.")
