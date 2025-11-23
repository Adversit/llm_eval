/**
 * FLMM Questionnaire Platform API Service - 扩展版本
 * 支持完整的项目创建、数据结构读取、证明材料上传等功能
 */
import api from './api';

// ========== 原有数据类型 ==========

export interface Question {
  question_id: string;
  question_text: string;
  question_type: 'single_choice' | 'multiple_choice' | 'text' | 'rating';
  options?: string[];
  required: boolean;
}

export interface Questionnaire {
  questionnaire_id: string;
  title: string;
  description?: string;
  questions: Question[];
  created_at: string;
  status: 'draft' | 'published' | 'closed';
}

export interface QuestionnaireCreateRequest {
  title: string;
  description?: string;
  questions: Question[];
}

export interface QuestionnaireCreateResponse {
  success: boolean;
  message: string;
  questionnaire_id: string;
}

export interface QuestionnaireResponse {
  response_id: string;
  questionnaire_id: string;
  answers: Record<string, any>;
  submitted_at: string;
}

export interface QuestionnaireSubmitResponse {
  success: boolean;
  message: string;
  response_id: string;
}

export interface QuestionnaireAnalysis {
  success: boolean;
  questionnaire_id: string;
  total_responses: number;
  completion_rate: number;
  question_stats: Record<string, {
    question_text: string;
    total_answers: number;
    answer_distribution: Record<string, number>;
  }>;
  created_at: string;
}

export interface FLMMStats {
  total_questionnaires: number;
  total_responses: number;
  published_questionnaires: number;
  total_projects: number;
  avg_responses_per_questionnaire: number;
}

export interface QuestionnaireListResponse {
  success: boolean;
  questionnaires: Questionnaire[];
}

// ========== 新增数据类型 ==========

/**
 * FLMM数据结构 - 四层级嵌套
 * 能力域 -> 能力子域1 -> 能力子域2 -> 能力项 -> 问题列表
 */
export interface FLMMStructure {
  [domain: string]: {
    [subdomain1: string]: {
      [subdomain2: string]: {
        [item: string]: string[];  // 问题列表
      };
    };
  };
}

export interface FLMMStructureResponse {
  success: boolean;
  structure: FLMMStructure;
  stats: {
    total_domains: number;
    total_items: number;
    total_questions: number;
  };
}

export interface EvidenceStructureResponse {
  success: boolean;
  structure: {
    [domain: string]: {
      [subdomain1: string]: {
        [subdomain2: string]: string[];  // 能力项列表
      };
    };
  };
  stats: {
    total_domains: number;
    total_items: number;
  };
}

export interface FunctionModule {
  name: string;
  description: string;
}

export interface SelectedItem {
  domain: string;
  subdomain1: string;
  subdomain2?: string;
  item: string;
  questions?: string[];
  question_count?: number;
}

export interface ProjectCreateRequest {
  company_name: string;
  scenario_name: string;
  scenario_description: string;
  functions_list: FunctionModule[];
  selected_questionnaire_items: SelectedItem[];
  selected_evidence_items?: SelectedItem[];
  enable_questionnaire: boolean;
  enable_evidence: boolean;
  auto_generate_account: boolean;
  username?: string;
  password?: string;
}

export interface ProjectCreateResponse {
  success: boolean;
  message: string;
  project_id: string;
  folder_name: string;
  generated_files: string[];
  account: {
    username: string;
    password: string;
    login_url?: string;
  };
}

export interface ProjectInfo {
  folder_name: string;
  project_id: string;
  company_name: string;
  scenario_name: string;
  created_time: string;
  status: string;
  questionnaire_enabled: boolean;
  evidence_enabled: boolean;
}

export interface ProjectsListResponse {
  success: boolean;
  projects: ProjectInfo[];
  total: number;
}

export interface EvidenceUploadResponse {
  success: boolean;
  message: string;
  files: {
    filename: string;
    size: number;
  }[];
}

// ========== API服务 ==========

export const flmmService = {
  // ========== 数据结构API ==========

  /**
   * 获取FLMM调研表数据结构
   */
  getQuestionnaireStructure: async (): Promise<FLMMStructureResponse> => {
    const response = await api.get<FLMMStructureResponse>('/flmm/structure/questionnaire');
    return response as any as FLMMStructureResponse;
  },

  /**
   * 获取FLMM自评表数据结构（用于证明材料收集）
   */
  getEvidenceStructure: async (): Promise<EvidenceStructureResponse> => {
    const response = await api.get<EvidenceStructureResponse>('/flmm/structure/evidence');
    return response as any as EvidenceStructureResponse;
  },

  // ========== 项目管理API ==========

  /**
   * 创建FLMM评估项目
   */
  createProject: async (data: ProjectCreateRequest): Promise<ProjectCreateResponse> => {
    const response = await api.post<ProjectCreateResponse>('/flmm/project/create', data);
    return response as any as ProjectCreateResponse;
  },

  /**
   * 获取所有项目列表
   */
  listProjects: async (): Promise<ProjectsListResponse> => {
    const response = await api.get<ProjectsListResponse>('/flmm/projects');
    return response as any as ProjectsListResponse;
  },

  /**
   * 获取项目详情
   */
  getProject: async (projectId: string): Promise<{success: boolean; project: any}> => {
    const response = await api.get(`/flmm/project/${projectId}`);
    return response as any;
  },

  // ========== 证明材料上传API ==========

  /**
   * 上传证明材料文件
   */
  uploadEvidenceFiles: async (
    projectFolder: string,
    capabilityItem: string,
    files: File[]
  ): Promise<EvidenceUploadResponse> => {
    const formData = new FormData();
    formData.append('project_folder', projectFolder);
    formData.append('capability_item', capabilityItem);

    files.forEach(file => {
      formData.append('files', file);
    });

    const response = await api.post<EvidenceUploadResponse>('/flmm/evidence/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response as any as EvidenceUploadResponse;
  },

  // ========== 原有基础功能API ==========

  /**
   * Create questionnaire
   */
  createQuestionnaire: async (data: QuestionnaireCreateRequest): Promise<QuestionnaireCreateResponse> => {
    const response = await api.post<QuestionnaireCreateResponse>('/flmm/questionnaire', data);
    return response as any as QuestionnaireCreateResponse;
  },

  /**
   * Get questionnaire details
   */
  getQuestionnaire: async (questionnaireId: string): Promise<Questionnaire> => {
    const response = await api.get<Questionnaire>(`/flmm/questionnaire/${questionnaireId}`);
    return response as any as Questionnaire;
  },

  /**
   * Get all questionnaires
   */
  listQuestionnaires: async (): Promise<QuestionnaireListResponse> => {
    const response = await api.get<QuestionnaireListResponse>('/flmm/questionnaires');
    return response as any as QuestionnaireListResponse;
  },

  /**
   * Submit questionnaire response
   */
  submitResponse: async (data: {
    questionnaire_id: string;
    answers: Record<string, any>;
  }): Promise<QuestionnaireSubmitResponse> => {
    const response = await api.post<QuestionnaireSubmitResponse>('/flmm/response', {
      response_id: '',
      questionnaire_id: data.questionnaire_id,
      answers: data.answers,
      submitted_at: new Date().toISOString(),
    });
    return response as any as QuestionnaireSubmitResponse;
  },

  /**
   * Get questionnaire analysis
   */
  getAnalysis: async (questionnaireId: string): Promise<QuestionnaireAnalysis> => {
    const response = await api.get<QuestionnaireAnalysis>(`/flmm/analysis/${questionnaireId}`);
    return response as any as QuestionnaireAnalysis;
  },

  /**
   * Get FLMM platform statistics
   */
  getStats: async (): Promise<FLMMStats> => {
    const response = await api.get<FLMMStats>('/flmm/stats');
    return response as any as FLMMStats;
  },

  // ========== 高级分析API ==========

  /**
   * 获取所有可分析的FLMM评估项目
   */
  getAnalysisProjects: async (): Promise<{
    success: boolean;
    projects: any[];
    total: number;
  }> => {
    return api.get('/flmm/analysis/projects');
  },

  /**
   * 获取项目的基本统计信息
   */
  getProjectStatistics: async (projectFolder: string): Promise<{
    success: boolean;
    statistics: {
      total_responses: number;
      total_questions: number;
      single_choice_count: number;
      multiple_choice_count: number;
    };
  }> => {
    const response = await api.get(`/flmm/analysis/project/${projectFolder}/statistics`);
    return response as any;
  },

  /**
   * 获取项目的逐题分析结果
   */
  getProjectQuestions: async (projectFolder: string): Promise<{
    success: boolean;
    questions: Array<{
      question_num: number;
      question_text: string;
      question_type: string;
      total_responses: number;
      answer_distribution: Record<string, number>;
      option_mapping: Record<string, string>;
    }>;
    total: number;
  }> => {
    const response = await api.get(`/flmm/analysis/project/${projectFolder}/questions`);
    return response as any;
  },

  /**
   * 获取项目的5个维度评级
   */
  getProjectRatings: async (projectFolder: string): Promise<{
    success: boolean;
    ratings: Record<string, {
      name: string;
      score: number;
      description: string;
      details: any;
    }>;
  }> => {
    const response = await api.get(`/flmm/analysis/project/${projectFolder}/ratings`);
    return response as any;
  },
};
