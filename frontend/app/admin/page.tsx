'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { API_URL } from '@/config';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';

export default function AdminDashboard() {
    const [globalTitle, setGlobalTitle] = useState('');
    const [globalContent, setGlobalContent] = useState('');
    const [facultyTitle, setFacultyTitle] = useState('');
    const [facultyContent, setFacultyContent] = useState('');
    const router = useRouter();

    useEffect(() => {
        const token = localStorage.getItem('token');
        const role = localStorage.getItem('role');

        if (!token || role !== 'Admin') {
            router.push('/login');
        }
    }, [router]);

    const handlePostGlobalAnnouncement = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const userId = localStorage.getItem('user_id') || 'admin';
            await axios.post(`${API_URL}/announcements`, {
                title: globalTitle,
                content: globalContent,
                type: 'Global',
                posted_by: userId
            });
            alert('Global Announcement posted!');
            setGlobalTitle('');
            setGlobalContent('');
        } catch (error: any) {
            console.error("Error posting announcement", error);
            const msg = error?.response?.data?.detail || error?.message || 'Failed to post announcement';
            alert(`Failed to post announcement: ${msg}`);
        }
    };

    return (
        <div className="min-h-screen flex flex-col bg-gray-50">
            <Navbar />
            <div className="container mx-auto px-4 py-8 flex-grow">
                <h1 className="text-3xl font-bold mb-8 text-blue-900">Admin Dashboard</h1>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Post Global Announcement */}
                    <div className="bg-white p-6 rounded-lg shadow-md">
                        <h2 className="text-xl font-bold mb-4 border-b pb-2">Post Global Announcement</h2>
                        <form onSubmit={handlePostGlobalAnnouncement} className="space-y-4">
                            <div>
                                <label className="block text-gray-700 font-medium mb-1">Title</label>
                                <input
                                    type="text"
                                    value={globalTitle}
                                    onChange={(e) => setGlobalTitle(e.target.value)}
                                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-gray-700 font-medium mb-1">Content</label>
                                <textarea
                                    value={globalContent}
                                    onChange={(e) => setGlobalContent(e.target.value)}
                                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    rows={4}
                                    required
                                />
                            </div>
                            <button type="submit" className="bg-red-600 text-white px-6 py-2 rounded-lg hover:bg-red-700">Post Global</button>
                        </form>
                    </div>

                    {/* Post To Faculty Announcement */}
                    <div className="bg-white p-6 rounded-lg shadow-md">
                        <h2 className="text-xl font-bold mb-4 border-b pb-2">Post Announcement to Faculty</h2>
                        <form onSubmit={async (e) => {
                            e.preventDefault();
                            try {
                                const userId = localStorage.getItem('user_id') || 'admin';
                                await axios.post(`${API_URL}/announcements`, {
                                    title: facultyTitle,
                                    content: facultyContent,
                                    type: 'Faculty',
                                    posted_by: userId
                                });
                                alert('Announcement posted to Faculty!');
                                setFacultyTitle('');
                                setFacultyContent('');
                            } catch (error: any) {
                                console.error('Error posting faculty announcement', error);
                                const msg = error?.response?.data?.detail || error?.message || 'Failed to post announcement to Faculty';
                                alert(`Failed to post announcement to Faculty: ${msg}`);
                            }
                        }} className="space-y-4">
                            <div>
                                <label className="block text-gray-700 font-medium mb-1">Title</label>
                                <input
                                    type="text"
                                    value={facultyTitle}
                                    onChange={(e) => setFacultyTitle(e.target.value)}
                                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-gray-700 font-medium mb-1">Content</label>
                                <textarea
                                    value={facultyContent}
                                    onChange={(e) => setFacultyContent(e.target.value)}
                                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    rows={4}
                                    required
                                />
                            </div>
                            <button type="submit" className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700">Post to Faculty</button>
                        </form>
                    </div>    

                    {/* System Settings Placeholder */}
                    <div className="bg-white p-6 rounded-lg shadow-md">
                        <h2 className="text-xl font-bold mb-4 border-b pb-2">System Settings</h2>
                        <p className="text-gray-600">Manage users, reset passwords, etc.</p>
                        <button className="mt-4 bg-gray-200 text-gray-700 px-4 py-2 rounded hover:bg-gray-300">Manage Users</button>
                    </div>
                </div>
            </div>
            <Footer />
        </div>
    );
}
