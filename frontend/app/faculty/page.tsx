'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { API_URL } from '@/config';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import { BookOpen, ChevronRight, Megaphone, Beaker, Camera } from 'lucide-react';

export default function FacultyDashboard() {
    const [faculty, setFaculty] = useState<any>(null);
    const [theoryCourses, setTheoryCourses] = useState<any[]>([]);
    const [labCourses, setLabCourses] = useState<any[]>([]);
    const [announcement, setAnnouncement] = useState({ title: '', content: '' });
    const [message, setMessage] = useState('');
    const [facultyAnnouncements, setFacultyAnnouncements] = useState<any[]>([]);
    const [facultyProfilePic, setFacultyProfilePic] = useState<string | null>(null);
    const router = useRouter();

    useEffect(() => {
        const token = localStorage.getItem('token');
        const role = localStorage.getItem('role');
        const userId = localStorage.getItem('user_id');

        if (!token || (role !== 'Faculty' && role !== 'HOD')) {
            router.push('/login');
            return;
        }

        const fetchData = async () => {
            try {
                // 1. Fetch faculty profile
                const res = await axios.get(`${API_URL}/faculty/${userId}`);
                setFaculty(res.data);
                setFacultyProfilePic(res.data.profile_pic || `https://ui-avatars.com/api/?name=${res.data.name}&background=random`);

                // 2. Fetch faculty-targeted announcements
                try {
                    const annRes = await axios.get(`${API_URL}/announcements?type=Faculty`);
                    setFacultyAnnouncements(annRes.data || []);
                } catch (err) {
                    console.warn('Could not fetch faculty announcements', err);
                }

                // 3. Courses Data - Splitting Theory and Labs
                // In a real app, this comes from your backend. 
                // We use .filter() to separate them based on the Title
                const allCourses = [
                    { id: 1, code: "CS3401", title: "Artificial Intelligence", sections: ["A", "B"] },
                    { id: 2, code: "MA3151", title: "Matrices & Calculus", sections: ["A"] },
                    { id: 3, code: "CS3402", title: "Data Science Lab", sections: ["A"] },
                    { id: 4, code: "CS3403", title: "Python Programming Lab", sections: ["A"] }
                ];

                setTheoryCourses(allCourses.filter(c => !c.title.toLowerCase().includes('lab')));
                setLabCourses(allCourses.filter(c => c.title.toLowerCase().includes('lab')));

            } catch (error) {
                console.error("Error loading profile:", error);
            }
        };
        fetchData();
    }, [router]);

    const handlePostAnnouncement = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const userId = localStorage.getItem('user_id');
            const payload = {
                title: announcement.title,
                content: announcement.content,
                type: "Department",
                posted_by: userId,
                course_code: "Global"
            };
            await axios.post(`${API_URL}/announcements`, payload);
            setMessage("Broadcasted to Department Successfully!");
            setAnnouncement({ title: '', content: '' });
            setTimeout(() => setMessage(''), 3000);
        } catch (err: any) {
            const msg = err?.response?.data?.detail || err?.message || 'Failed to post';
            setMessage(`Failed to post announcement: ${msg}`);
            setTimeout(() => setMessage(''), 4000);
        }
    };

    if (!faculty) return <div className="min-h-screen flex items-center justify-center font-bold text-blue-900">Loading Staff Portal...</div>;

    return (
        <div className="min-h-screen flex flex-col bg-gray-50">
            <Navbar />
            <div className="container mx-auto px-4 py-8 flex-grow">
                <div className="flex justify-between items-center mb-8">
                    <h1 className="text-3xl font-bold text-blue-900">Faculty Dashboard</h1>
                    <span className="bg-blue-100 text-blue-800 px-4 py-1 rounded-full font-semibold uppercase text-xs">
                        {faculty.designation}
                    </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {/* LEFT COLUMN: Profile Card */}
                    <div className="bg-white p-6 rounded-lg shadow-md h-fit border-t-4 border-blue-900">
                        <div className="flex flex-col items-center mb-4">
                            <div className="relative group w-24 h-24">
                                <img src={facultyProfilePic || ''} alt="Profile" className="w-24 h-24 rounded-full object-cover border-4 border-gray-200 shadow-sm mb-4" />
                                <label className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 rounded-full opacity-0 group-hover:opacity-100 transition cursor-pointer text-white">
                                    <Camera size={20} />
                                    <input type="file" className="hidden" accept="image/*" onChange={async (e) => {
                                        if (!(e.target.files && e.target.files[0])) return;
                                        const file = e.target.files[0];
                                        setFacultyProfilePic(URL.createObjectURL(file));
                                        const userId = localStorage.getItem('user_id') || faculty.staff_no;
                                        const form = new FormData();
                                        form.append('file', file);
                                        try {
                                            const res = await axios.post(`${API_URL}/faculty/${userId}/photo`, form, { headers: { 'Content-Type': 'multipart/form-data' } });
                                            const newUrl = res.data.profile_pic;
                                            if (newUrl) {
                                                setFacultyProfilePic(newUrl);
                                                setFaculty({ ...faculty, profile_pic: newUrl });
                                            }
                                            alert('Profile photo updated');
                                        } catch (err: any) {
                                            console.error('Upload failed', err);
                                            const msg = err?.response?.data?.detail || err?.message || 'Upload failed';
                                            alert(`Failed to upload photo: ${msg}`);
                                        }
                                    }} />
                                </label>
                            </div>
                            <h2 className="text-xl font-bold text-blue-900 text-center">{faculty.name}</h2>
                        </div>
                        <div className="space-y-3 text-sm border-t pt-4 font-medium">
                            <p className="flex justify-between"><span className="text-gray-500">Staff ID:</span> <span className="font-mono font-bold text-blue-900">{faculty.staff_no}</span></p>
                            <p className="flex justify-between"><span className="text-gray-500">Dept:</span> <span className="font-bold">AI & DS</span></p>
                        </div>
                    </div>

                    {/* RIGHT COLUMN: Main Actions */}
                    <div className="md:col-span-2 space-y-8">
                        
                        {/* Faculty Announcements */}
                        <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-indigo-600">
                            <h2 className="text-xl font-bold mb-4 text-indigo-900 flex items-center gap-2">
                                <Megaphone className="text-indigo-600" /> Announcements for Faculty
                            </h2>
                            {facultyAnnouncements.length === 0 ? (
                                <p className="text-gray-500">No announcements for faculty.</p>
                            ) : (
                                <div className="space-y-3">
                                    {facultyAnnouncements.map((a: any) => (
                                        <div key={a.id} className="p-3 border rounded-md bg-indigo-50">
                                            <h3 className="font-bold text-indigo-900">{a.title}</h3>
                                            <p className="text-sm text-gray-700">{a.content}</p>
                                            <p className="text-xs text-gray-400 mt-1">Posted by: {a.posted_by}</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* 1. THEORY COURSES SECTION */}
                        <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-blue-600">
                            <h2 className="text-xl font-bold mb-4 text-blue-900 flex items-center gap-2">
                                <BookOpen className="text-blue-600" /> Theory Management
                            </h2>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                {theoryCourses.map((course) => (
                                    <div key={course.id} className="border rounded-lg p-4 bg-gray-50 hover:border-blue-500 transition-all group">
                                        <h3 className="font-bold text-blue-900">{course.code}</h3>
                                        <p className="text-xs text-gray-500 mb-3">{course.title}</p>
                                        <div className="flex flex-wrap gap-2">
                                            {course.sections.map((sec: string) => (
                                                <button
                                                    key={sec}
                                                    onClick={() => router.push(`/faculty/manage/${course.code}/${sec}`)}
                                                    className="bg-blue-900 text-white px-3 py-1.5 rounded text-xs font-bold hover:bg-orange-500 flex items-center gap-1 transition-colors"
                                                >
                                                    Sec {sec} <ChevronRight size={12} />
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* 2. LABORATORY COURSES SECTION */}
                        <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-purple-600">
                            <h2 className="text-xl font-bold mb-4 text-purple-900 flex items-center gap-2">
                                <Beaker className="text-purple-600" /> Laboratory Management
                            </h2>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                {labCourses.map((lab) => (
                                    <div key={lab.id} className="border rounded-lg p-4 bg-purple-50/30 hover:border-purple-500 transition-all group">
                                        <h3 className="font-bold text-purple-900">{lab.code}</h3>
                                        <p className="text-xs text-gray-500 mb-3">{lab.title}</p>
                                        <div className="flex flex-wrap gap-2">
                                            {lab.sections.map((sec: string) => (
                                                <button
                                                    key={sec}
                                                    onClick={() => router.push(`/faculty/manage/${lab.code}/${sec}`)}
                                                    className="bg-purple-600 text-white px-3 py-1.5 rounded text-xs font-bold hover:bg-orange-500 flex items-center gap-1 transition-colors"
                                                >
                                                    Lab Sec {sec} <ChevronRight size={12} />
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Announcement Form */}
                        <div className="bg-white p-6 rounded-lg shadow-md border-t-4 border-orange-500">
                            <h2 className="text-xl font-bold mb-4 text-blue-900 flex items-center gap-2">
                                <Megaphone className="text-orange-500" /> Post Dept. Announcement
                            </h2>
                            {message && <p className="mb-4 p-2 bg-green-100 text-green-700 rounded text-xs text-center font-bold animate-pulse">{message}</p>}
                            <form onSubmit={handlePostAnnouncement} className="space-y-4">
                                <input
                                    className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 outline-none font-medium"
                                    placeholder="Title..."
                                    value={announcement.title}
                                    onChange={(e) => setAnnouncement({ ...announcement, title: e.target.value })}
                                    required
                                />
                                <textarea
                                    className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 outline-none h-20 font-medium"
                                    placeholder="Details..."
                                    value={announcement.content}
                                    onChange={(e) => setAnnouncement({ ...announcement, content: e.target.value })}
                                    required
                                />
                                <button type="submit" className="w-full bg-orange-500 text-white font-bold py-2 rounded hover:bg-orange-600 transition uppercase text-xs tracking-widest shadow-md">
                                    Broadcast to Department
                                </button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
            <Footer />
        </div>
    );
}