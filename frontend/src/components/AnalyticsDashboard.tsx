import React from "react";
import { X, TrendingDown, Clock, Activity } from "lucide-react";
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import type { DispatchResult } from "../types";

interface Props {
    history: DispatchResult[];
    onClose: () => void;
}

export default function AnalyticsDashboard({ history, onClose }: Props) {
    const data = React.useMemo(() => history.map((res, i) => ({
        name: `#${res.emergency_id.substring(0, 4)}`,
        Response: parseFloat(res.response_time.toFixed(1)),
        Transport: parseFloat(res.transport_time.toFixed(1)),
        Total: parseFloat(res.total_time.toFixed(1)),
        Algorithm: res.algorithm,
    })), [history]);

    const stats = React.useMemo(() => {
        if (data.length === 0) return { avgTotal: "0.0", avgResponse: "0.0" };
        const total = data.reduce((sum, d) => sum + d.Total, 0) / data.length;
        const resp = data.reduce((sum, d) => sum + d.Response, 0) / data.length;
        return {
            avgTotal: total.toFixed(1),
            avgResponse: resp.toFixed(1),
        };
    }, [data]);

    const { avgTotal, avgResponse } = stats;

    return (
        <div className="modal-overlay">
            <div className="modal-content" style={{ maxWidth: '800px', width: '90%' }}>
                <header className="modal-header">
                    <div className="modal-title">
                        <Activity /> Analytics & Performance
                    </div>
                    <button className="btn-icon" onClick={onClose} aria-label="Close">
                        <X size={20} />
                    </button>
                </header>

                <div className="modal-body">
                    <div className="stats-row" style={{ marginBottom: '24px' }}>
                        <div className="stat-box" style={{ flex: 1, padding: '16px' }}>
                            <span className="stat-lbl"><Clock size={14} /> Avg Total Time</span>
                            <span className="stat-num" style={{ fontSize: '24px' }}>{avgTotal} <span style={{ fontSize: '14px', color: 'var(--m3-outline)' }}>min</span></span>
                        </div>
                        <div className="stat-box" style={{ flex: 1, padding: '16px' }}>
                            <span className="stat-lbl"><TrendingDown size={14} /> Avg Response Time</span>
                            <span className="stat-num" style={{ fontSize: '24px' }}>{avgResponse} <span style={{ fontSize: '14px', color: 'var(--m3-outline)' }}>min</span></span>
                        </div>
                        <div className="stat-box" style={{ flex: 1, padding: '16px' }}>
                            <span className="stat-lbl"><Activity size={14} /> Dispatches Tracked</span>
                            <span className="stat-num" style={{ fontSize: '24px' }}>{history.length}</span>
                        </div>
                    </div>

                    <div className="card-title">Dispatch Time History</div>
                    <div style={{ height: '300px', width: '100%', marginTop: '16px' }}>
                        {data.length === 0 ? (
                            <div className="hint" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                No dispatch history available yet. Run a dispatch to see analytics.
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="var(--m3-outline-variant)" vertical={false} />
                                    <XAxis dataKey="name" stroke="var(--m3-on-surface-var)" fontSize={12} tickLine={false} />
                                    <YAxis stroke="var(--m3-on-surface-var)" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(val: number) => `${val}m`} />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: 'var(--m3-surface-container-high)',
                                            border: '1px solid var(--m3-outline-variant)',
                                            borderRadius: '8px',
                                            color: 'var(--m3-on-surface)'
                                        }}
                                        labelStyle={{ color: 'var(--m3-on-surface-var)', marginBottom: '8px' }}
                                        itemStyle={{ fontSize: '14px', fontWeight: 'bold' }}
                                    />
                                    <Line
                                        type="monotone"
                                        name="Total Time"
                                        dataKey="Total"
                                        stroke="var(--m3-primary)"
                                        strokeWidth={3}
                                        dot={{ fill: 'var(--m3-primary)', r: 4 }}
                                        activeDot={{ r: 6 }}
                                    />
                                    <Line
                                        type="monotone"
                                        name="Response Time"
                                        dataKey="Response"
                                        stroke="var(--m3-tertiary)"
                                        strokeWidth={2}
                                        dot={{ fill: 'var(--m3-tertiary)', r: 3 }}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
