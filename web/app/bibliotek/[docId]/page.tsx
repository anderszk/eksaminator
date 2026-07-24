export default function BibliotekPage({ params }: { params: { docId: string } }) {
  return (
    <div>
      <p>Bibliotek — {params.docId}</p>
    </div>
  );
}
