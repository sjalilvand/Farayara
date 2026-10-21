import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Catalog from './pages/Catalog'
import FieldDetail from './pages/FieldDetail'
import Forms from './pages/Forms'
import FormBuilder from './pages/FormBuilder'
import FormFill from './pages/FormFill'
import Submissions from './pages/Submissions'
import Processes from './pages/Processes'
import ProcessDetail from './pages/ProcessDetail'
import MyTasks from './pages/MyTasks'
import TaskDetail from './pages/TaskDetail'
import Assessments from './pages/Assessments'
import AssessmentDetail from './pages/AssessmentDetail'
import AssessmentRun from './pages/AssessmentRun'
import AssessmentResults from './pages/AssessmentResults'
import ContractTemplates from './pages/ContractTemplates'
import TemplateEditor from './pages/TemplateEditor'
import Contracts from './pages/Contracts'
import Users from './pages/Users'
import AuditLogs from './pages/AuditLogs'
import Settings from './pages/Settings'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isLoggedIn } = useAuth()
  if (!isLoggedIn) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="catalog" element={<Catalog />} />
          <Route path="catalog/:id" element={<FieldDetail />} />
          <Route path="forms" element={<Forms />} />
          <Route path="forms/:id/edit" element={<FormBuilder />} />
          <Route path="forms/:id/submissions" element={<Submissions />} />
          <Route path="fill/:versionId" element={<FormFill />} />
          <Route path="processes" element={<Processes />} />
          <Route path="processes/:id" element={<ProcessDetail />} />
          <Route path="tasks" element={<MyTasks />} />
          <Route path="tasks/:id" element={<TaskDetail />} />
          <Route path="assessments" element={<Assessments />} />
          <Route path="assessments/:id" element={<AssessmentDetail />} />
          <Route path="assessments/:id/run" element={<AssessmentRun />} />
          <Route path="assessment-administrations/:id/result" element={<AssessmentResults />} />
          <Route path="contract-templates" element={<ContractTemplates />} />
          <Route path="contract-templates/:id/edit" element={<TemplateEditor />} />
          <Route path="contracts" element={<Contracts />} />
          <Route path="users" element={<Users />} />
          <Route path="audit" element={<AuditLogs />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
