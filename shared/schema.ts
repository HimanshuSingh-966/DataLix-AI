import { sql } from "drizzle-orm";
import { pgTable, text, varchar, timestamp, integer, jsonb, decimal, uuid } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// Profiles table (linked to Supabase auth.users)
export const profiles = pgTable("profiles", {
  id: uuid("id").primaryKey(),
  username: text("username").notNull().unique(),
  email: text("email").notNull().unique(),
  isMaster: integer("is_master").notNull().default(0),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const insertProfileSchema = createInsertSchema(profiles).omit({
  id: true,
  isMaster: true,
  createdAt: true,
});

export type InsertProfile = z.infer<typeof insertProfileSchema>;
export type Profile = typeof profiles.$inferSelect;

// Legacy type aliases for backward compatibility
export type User = Profile;
export type InsertUser = InsertProfile;

// Datasets table (stores uploaded dataset data for persistence)
export const datasets = pgTable("datasets", {
  id: uuid("id").primaryKey().default(sql`gen_random_uuid()`),
  sessionId: uuid("session_id").notNull().references(() => sessions.id, { onDelete: "cascade" }),
  userId: uuid("user_id").notNull().references(() => profiles.id),
  fileName: text("file_name"),
  dataCsv: text("data_csv"),
  dataPreview: jsonb("data_preview"),
  qualityScore: jsonb("quality_score"),
  metadata: jsonb("metadata"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

export const insertDatasetSchema = createInsertSchema(datasets).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type InsertDataset = z.infer<typeof insertDatasetSchema>;
export type DatasetRow = typeof datasets.$inferSelect;

// Sessions table
export const sessions = pgTable("sessions", {
  id: uuid("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: uuid("user_id").notNull().references(() => profiles.id),
  name: text("name"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

export const insertSessionSchema = createInsertSchema(sessions).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type InsertSession = z.infer<typeof insertSessionSchema>;
export type Session = typeof sessions.$inferSelect;

// Messages table
export const messages = pgTable("messages", {
  id: uuid("id").primaryKey().default(sql`gen_random_uuid()`),
  sessionId: uuid("session_id").notNull().references(() => sessions.id),
  role: text("role").notNull(), // 'user' | 'assistant'
  content: text("content").notNull(),
  chartData: jsonb("chart_data"), // Plotly chart JSON
  dataPreview: jsonb("data_preview"), // Table data preview
  suggestedActions: jsonb("suggested_actions"), // Array of action objects
  functionCalls: jsonb("function_calls"), // AI function calls made
  error: text("error"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const insertMessageSchema = createInsertSchema(messages).omit({
  id: true,
  createdAt: true,
});

export type InsertMessage = z.infer<typeof insertMessageSchema>;
export type Message = typeof messages.$inferSelect;

// TypeScript interfaces for runtime data structures

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  chartData?: PlotlyChartData;
  dataPreview?: DataPreview;
  qualityScore?: DataQuality;
  suggestedActions?: SuggestedAction[];
  functionCalls?: string[];
  auditLog?: any[];
  insightSummary?: string;
  error?: boolean;
}

export interface SuggestedAction {
  label: string;
  prompt: string;
  icon?: string;
}

export interface DataPreview {
  columns: ColumnInfo[];
  rows: Record<string, any>[];
  totalRows: number;
  totalColumns: number;
  fileName?: string;
}

export interface ColumnInfo {
  name: string;
  type: string;
  nullCount: number;
  uniqueCount: number;
  sampleValues: any[];
}

export interface DataQuality {
  overallScore: number;
  completeness: number;
  consistency: number;
  uniqueness: number;
  validity: number;
  columnMetrics: ColumnMetric[];
  issues: QualityIssue[];
  recommendations: string[];
}

export interface ColumnMetric {
  column: string;
  missingPercentage: number;
  uniqueValues: number;
  dataType: string;
  sampleValues: any[];
}

export interface QualityIssue {
  type: 'missing_values' | 'duplicates' | 'outliers' | 'inconsistency';
  severity: 'high' | 'medium' | 'low';
  column?: string;
  count: number;
  description: string;
}

export interface PlotlyChartData {
  data: any[];
  layout: any;
  config?: any;
}

export interface StatisticResult {
  column: string;
  mean?: number;
  median?: number;
  std?: number;
  min?: number;
  max?: number;
  count?: number;
  q25?: number;
  q75?: number;
}

export interface CorrelationMatrix {
  columns: string[];
  matrix: number[][];
}

export interface ImputationResult {
  column: string;
  missingBefore: number;
  missingAfter: number;
  imputed: number;
  method: string;
}

export interface OutlierResult {
  method: string;
  rowsBefore: number;
  rowsAfter: number;
  totalRemoved: number;
  outliersByColumn: Record<string, number>;
}

export interface DuplicateResult {
  rowsRemoved: number;
  rowsBefore: number;
  rowsAfter: number;
  percentage: number;
}

export interface MLAnalysisResult {
  analysisType: 'anomaly_detection' | 'clustering' | 'dimensionality_reduction' | 'feature_importance';
  algorithm: string;
  results: any;
  visualization?: PlotlyChartData;
  metrics?: Record<string, number>;
}

export interface FilterCondition {
  column: string;
  operator: '>' | '<' | '==' | '!=' | '>=' | '<=' | 'contains' | 'regex' | 'between' | 'is_null' | 'not_null';
  value?: any;
  value2?: any; // For 'between' operator
}

export interface FilterRequest {
  conditions: FilterCondition[];
  logic: 'AND' | 'OR';
}

export interface TransformRequest {
  operation: 'normalize' | 'log' | 'sqrt' | 'boxcox' | 'pivot' | 'melt' | 'aggregate' | 'merge' | 'sort' | 'sample';
  columns?: string[];
  parameters?: Record<string, any>;
}

export interface FeatureEngineeringRequest {
  type: 'datetime' | 'binning' | 'polynomial' | 'interaction' | 'lag' | 'rolling';
  columns: string[];
  parameters?: Record<string, any>;
}

export interface ExportRequest {
  format: 'csv' | 'excel' | 'json' | 'parquet';
  filename?: string;
  delimiter?: string;
  compression?: boolean;
  encoding?: string;
  columnsToExport?: string[];
}

export interface UploadResponse {
  sessionId: string;
  datasetInfo: {
    rows: number;
    columns: number;
    sizeMb: number;
    columnNames: string[];
    columnTypes: Record<string, string>;
  };
  quality: DataQuality;
  preview: DataPreview;
  issues: QualityIssue[];
}

export interface ChatRequest {
  sessionId: string;
  message: string;
}

export interface ChatResponse {
  message: string;
  functionCalls?: string[];
  results?: any;
  dataPreview?: DataPreview;
  chartData?: PlotlyChartData;
  suggestedActions?: SuggestedAction[];
  qualityScore?: number;
}

// Validation schemas for API requests

export const chatRequestSchema = z.object({
  sessionId: z.string().uuid(),
  message: z.string().min(1).max(5000),
});

export const filterRequestSchema = z.object({
  conditions: z.array(z.object({
    column: z.string(),
    operator: z.enum(['>', '<', '==', '!=', '>=', '<=', 'contains', 'regex', 'between', 'is_null', 'not_null']),
    value: z.any().optional(),
    value2: z.any().optional(),
  })),
  logic: z.enum(['AND', 'OR']).default('AND'),
});

export const imputeRequestSchema = z.object({
  columns: z.array(z.string()),
  method: z.enum(['mean', 'median', 'mode', 'knn', 'forward_fill', 'backward_fill', 'interpolation', 'mice', 'model_based']),
  knnNeighbors: z.number().int().min(1).max(20).optional().default(5),
});

export const outlierRequestSchema = z.object({
  columns: z.array(z.string()),
  method: z.enum(['iqr', 'zscore', 'modified_zscore', 'isolation_forest', 'dbscan', 'grubbs', 'lof']),
  threshold: z.number().optional().default(1.5),
});

export const duplicateRequestSchema = z.object({
  subset: z.array(z.string()).optional(),
  keep: z.enum(['first', 'last', 'none']).default('first'),
  fuzzy: z.boolean().optional().default(false),
  threshold: z.number().min(0).max(1).optional().default(0.85),
});

export const encodeRequestSchema = z.object({
  columns: z.array(z.string()),
  method: z.enum(['label', 'onehot', 'ordinal', 'target']),
});

export const visualizationRequestSchema = z.object({
  chartType: z.enum([
    'histogram', 'scatter', 'line', 'bar', 'box', 'violin', 'heatmap', 
    'correlation', 'pie', 'donut', 'treemap', 'sunburst', '3d_scatter',
    '3d_surface', 'candlestick', 'waterfall', 'funnel', 'sankey'
  ]),
  xColumn: z.string().optional(),
  yColumn: z.string().optional(),
  zColumn: z.string().optional(),
  colorBy: z.string().optional(),
  title: z.string().optional(),
  parameters: z.record(z.any()).optional(),
});

export const exportRequestSchema = z.object({
  format: z.enum(['csv', 'excel', 'json', 'parquet']),
  filename: z.string().optional(),
  delimiter: z.string().optional().default(','),
  compression: z.boolean().optional().default(false),
  encoding: z.string().optional().default('utf-8'),
  columnsToExport: z.array(z.string()).optional(),
});

export const mlAnalysisRequestSchema = z.object({
  analysisType: z.enum(['anomaly_detection', 'clustering', 'dimensionality_reduction', 'feature_importance']),
  algorithm: z.string().optional(),
  parameters: z.record(z.any()).optional(),
});

export const statisticsRequestSchema = z.object({
  columns: z.array(z.string()).optional(),
  stats: z.array(z.enum(['mean', 'median', 'std', 'min', 'max', 'count', 'q25', 'q75', 'correlation'])).optional(),
});
