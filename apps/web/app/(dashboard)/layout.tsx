import { Sidebar } from "@/components/layout/sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-[#090d16]">
      <Sidebar />
      <main className="flex-1 pl-64 flex flex-col min-h-screen">
        {children}
      </main>
    </div>
  );
}
