export default function DataTable({ data }) {
    if (!data || data.length === 0) {
        return null;
    }

    const headers = Object.keys(data[0]);

    return (
        <div className="mt-4 mb-2 overflow-x-auto bg-white border border-gray-200 rounded-lg shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                    <tr>
                        {headers.map((header) => (
                            <th 
                                key={header} 
                                scope="col"
                                className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider"
                            >
                                {header}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                    {data.map((row, rowIndex) => (
                        <tr key={rowIndex} className="hover:bg-gray-50">
                            {headers.map((header, cellIndex) => (
                                <td 
                                    key={cellIndex} 
                                    className="px-4 py-3 text-sm text-gray-800 whitespace-nowrap"
                                >
                                    {row[header]}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

