import axios from "axios";
import type { ArchitectureResult, CodeElement, DeadCodeFinding, DiagramResult, QAResponse, Repository } from "../types";

const http = axios.create({ baseURL: "/api" });

export const api = {
  listRepositories: (): Promise<Repository[]> => http.get("/repositories").then(r => r.data),
  getRepository: (id: string): Promise<Repository> => http.get(`/repositories/${id}`).then(r => r.data),
  createRepository: (url: string, branch?: string): Promise<Repository> =>
    http.post("/repositories", { url, branch: branch || undefined }).then(r => r.data),
  deleteRepository: (id: string): Promise<void> => http.delete(`/repositories/${id}`).then(() => undefined),
  reanalyzeRepository: (id: string): Promise<Repository> => http.post(`/repositories/${id}/reanalyze`).then(r => r.data),
  getArchitecture: (id: string): Promise<ArchitectureResult> => http.get(`/repositories/${id}/architecture`).then(r => r.data),
  getDiagrams: (id: string): Promise<DiagramResult> => http.get(`/repositories/${id}/diagrams`).then(r => r.data),
  getDeadCode: (id: string): Promise<{ findings: DeadCodeFinding[] }> => http.get(`/repositories/${id}/dead-code`).then(r => r.data),
  listCodeElements: (id: string, params?: any): Promise<CodeElement[]> =>
    http.get(`/repositories/${id}/elements`, { params }).then(r => r.data),
  askQuestion: (id: string, question: string, top_k = 8): Promise<QAResponse> =>
    http.post(`/repositories/${id}/ask`, { question, top_k }).then(r => r.data),
};
