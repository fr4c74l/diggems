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
from gevent import socket
from geventwebsocket.websocket import WebSocket
from geventwebsocket.logging import create_logger
from diggems.settings import DEBUG

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

_recv_buf = ffi.new('char[]', 4096)

def recv_with_fd(src_fd):
    global _recv_buf
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

    if flags[0] == socket.MSG_TRUNC:
        # TODO: do something if message is truncated
        # or better: never let it happen...
        pass

    subject_fd = subject_fd[0] if subject_fd[0] else None
    buf = ffi.buffer(buf)[:ret]

    return (buf, subject_fd)

def send_with_fd(dest_fd, message, subject_fd):
    buf = ffi.new('char[]', message)
    while 1:
        ret = C.send_with_fd(dest_fd.fileno(), buf, len(message), subject_fd)
        if ret >= 0:
            break
        if -ret in (errno.EPERM, errno.EWOULDBLOCK, errno.EAGAIN):
            select([], [dest_fd], [])
        else:
            raise os.error(-ret, os.strerror(-ret))
    return ret
