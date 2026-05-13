<template>
  <div class="app-shell">
    <aside class="sidebar">
      <h2>Secure File Platform</h2>
      <RouterLink to="/">Dashboard</RouterLink>
      <RouterLink to="/upload">Upload</RouterLink>
      <RouterLink to="/files">Files</RouterLink>
      <RouterLink to="/audit-logs">Audit Logs</RouterLink>
      <RouterLink to="/admin">Admin</RouterLink>
    </aside>
    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>
