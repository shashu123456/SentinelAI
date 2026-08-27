import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { organizations } from '../services/api';

const OrgContext = createContext(null);

export function OrgProvider({ children }) {
  const [currentOrg, setCurrentOrg] = useState(null);
  const [currentProject, setCurrentProject] = useState(null);
  const [orgs, setOrgs] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);

  // Load user's organizations
  const loadOrgs = useCallback(async () => {
    try {
      setLoading(true);
      const data = await organizations.list();
      setOrgs(data || []);

      // Restore last selected org from localStorage
      const savedOrgId = localStorage.getItem('sentinelai_org_id');
      if (savedOrgId) {
        const found = data?.find(o => o.id === Number(savedOrgId));
        if (found) {
          setCurrentOrg(found);
        }
      }
    } catch {
      setOrgs([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load projects for current org
  const loadProjects = useCallback(async (orgId) => {
    if (!orgId) {
      setProjects([]);
      return;
    }
    try {
      const data = await organizations.listProjects(orgId);
      setProjects(data || []);

      // Restore last selected project
      const savedProjectId = localStorage.getItem('sentinelai_project_id');
      if (savedProjectId) {
        const found = data?.find(p => p.id === Number(savedProjectId));
        if (found) {
          setCurrentProject(found);
        }
      }
    } catch {
      setProjects([]);
    }
  }, []);

  useEffect(() => {
    loadOrgs();
  }, [loadOrgs]);

  useEffect(() => {
    if (currentOrg) {
      loadProjects(currentOrg.id);
    } else {
      setProjects([]);
      setCurrentProject(null);
    }
  }, [currentOrg, loadProjects]);

  const selectOrg = useCallback((org) => {
    setCurrentOrg(org);
    setCurrentProject(null);
    if (org) {
      localStorage.setItem('sentinelai_org_id', org.id);
    } else {
      localStorage.removeItem('sentinelai_org_id');
    }
    localStorage.removeItem('sentinelai_project_id');
  }, []);

  const selectProject = useCallback((project) => {
    setCurrentProject(project);
    if (project) {
      localStorage.setItem('sentinelai_project_id', project.id);
    } else {
      localStorage.removeItem('sentinelai_project_id');
    }
  }, []);

  const refreshOrgs = useCallback(() => loadOrgs(), [loadOrgs]);

  const refreshProjects = useCallback(() => {
    if (currentOrg) loadProjects(currentOrg.id);
  }, [currentOrg, loadProjects]);

  return (
    <OrgContext.Provider value={{
      currentOrg,
      currentProject,
      orgs,
      projects,
      loading,
      selectOrg,
      selectProject,
      refreshOrgs,
      refreshProjects,
    }}>
      {children}
    </OrgContext.Provider>
  );
}

export const useOrg = () => useContext(OrgContext);
