import cPickle as pickle
import traceback
import gevent
import gevent.socket
import gevent.os
import socket
import errno
import gipc
import os

from gevent.select import select

# TODO: Use python 3 for this stuff
#(Gevent on python 3? Pypy on python 3? Both? Unrealistic...)
from cffi import FFI

ffi = FFI()
ffi.cdef("""
    int send_with_fd(int dest_fd, char *buf, size_t size, int subject_fd);
    int recv_with_fd(int src_fd, char *buf4k, int *subject_fd, int *flags);
""")
C = ffi.verify("""
    #include <errno.h>
    #include <sys/types.h>
    #include <sys/socket.h>
    #include <sys/un.h>

    int send_with_fd(int dest_fd, char *buf, size_t size, int subject_fd) {
        struct msghdr msg = {0};
        struct iovec vec;
        struct cmsghdr *cmsg;
        char cbuf[CMSG_SPACE(sizeof(subject_fd))];

        vec.iov_base = buf;
        vec.iov_len = size;

        msg.msg_iov = &vec;
        msg.msg_iovlen = 1;
        msg.msg_control = cbuf;
        msg.msg_controllen = sizeof cbuf;
        cmsg = CMSG_FIRSTHDR(&msg);
        cmsg->cmsg_level = SOL_SOCKET;
        cmsg->cmsg_type = SCM_RIGHTS;
        cmsg->cmsg_len = CMSG_LEN(sizeof(int));

        /* Initialize the payload: */
        int *fdptr = (int *) CMSG_DATA(cmsg);
        *fdptr = subject_fd;

        /* Sum of the length of all control messages in the buffer: */
        msg.msg_controllen = cmsg->cmsg_len;

        return sendmsg(dest_fd, &msg, MSG_DONTWAIT);
    }

    int recv_with_fd(int src_fd, char *buf4k, int *subject_fd, int *flags) {
        int res;
        struct msghdr msg = {0};
        struct iovec vec;
        struct cmsghdr *cmsg;
        char cbuf[CMSG_SPACE(sizeof(int))];

        /* For the data that may arrive */
        vec.iov_base = buf4k;
        vec.iov_len = 4096;

        msg.msg_control = cbuf;
        msg.msg_controllen = CMSG_SPACE(sizeof(int));
        msg.msg_iov = &vec;
        msg.msg_iovlen = 1;

        if((res = recvmsg(src_fd, &msg, MSG_DONTWAIT)) <= 0)
            return -errno;

        /* Iterate through header to find if there is a file descriptor */
        for(cmsg = CMSG_FIRSTHDR(&msg); cmsg != NULL; cmsg = CMSG_NXTHDR(&msg, cmsg))
        {
            if((cmsg->cmsg_level == SOL_SOCKET) && (cmsg->cmsg_type == SCM_RIGHTS) )
            {
                *subject_fd = *(int*)CMSG_DATA(cmsg);
                break; /* At most one fd will be received. */
            }
        }

        *flags = msg.msg_flags;

        return res;
    }
""")

def recv_with_fd(src_fd):
    buf = ffi.new('char[]', 4096)
    while 1:
        select([src_fd], [], [])
        subject_fd = ffi.new('int *')
        subject_fd[0] = 0
        flags = ffi.new('int *')
        flags[0] = 0
        ret = C.recv_with_fd(src_fd.fileno(), buf, subject_fd, flags)
        if ret >= 0:
            break
        if -ret not in (errno.EWOULDBLOCK, errno.EAGAIN):
            raise os.error(-ret, os.strerror(-ret))

    print flags[0]
    subject_fd = subject_fd[0] if subject_fd[0] else None
    buf = ffi.buffer(buf)[:ret]

    return (buf, subject_fd)

def send_with_fd(dest_fd, message, subject_fd):
    buf = ffi.new('char[]', message)
    while 1:
        ret = C.send_with_fd(dest_fd.fileno(), buf, len(message), subject_fd)
        if ret >= 0:
            break
        if -ret not in (errno.EWOULDBLOCK, errno.EAGAIN):
            raise os.error(-ret, os.strerror(-ret))
        select([], [dest_fd.fileno()], [])
    if ret != len(message):
        print "Message not sent entirely!" 

i = 0

def sender():
    w = pipe[1]

    def next_msg():
        global i
        i += 1
        return 'msg {}'.format(i)

    def a():
        while 1:
            w.send(next_msg())
            gevent.sleep(1)
    gevent.spawn(a)

    def b():
        while 1:
            pair = os.pipe()
            map(gevent.os.make_nonblocking, pair)
            send_with_fd(w, next_msg(), pair[0])
            os.close(pair[0])

            def pipe_writer(w):
                for i in xrange(10):
                    gevent.sleep(0.1)
                    gevent.os.nb_write(w, next_msg())
                os.close(w)
            gevent.spawn(pipe_writer, pair[1])
            gevent.sleep(3)
    gevent.spawn(b)

def receiver():
    r = pipe[0]
    while 1:
        (msg, fd) = recv_with_fd(r)
        print msg
        if fd:
            def pipe_reader(r):
                msg = gevent.os.nb_read(r, 1024)
                while msg:
                    print 'Received from received pipe:', msg
                    msg = gevent.os.nb_read(r, 1024)
                os.close(r)
                print "done with pipe ", r
            gevent.spawn(pipe_reader, fd)

pipe = gevent.socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)

gipc.start_process(receiver)

sender()