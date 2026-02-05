import General_Nav from "../../components/General_Nav";

export default function HomeLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gray-50">

      <main className="flex-2">{children}</main>
    </div>
  );
}
