import cPickle as pickle
import gevent
import gevent.socket
import socket
import gipc
import os

# TODO: Use python 3 for this stuff
#(Gevent on python 3? Pypy on python 3? Both? Unrealistic...)
from cffi import FFI

ffi = FFI()
ffi.cdef("""
    int send_fd(int dest_fd, int subject_fd);
    int recv_buf_or_fd(int src_fd, char *buf4k);
""")
ffi.verify("""
    #include <errno.h>
    #include <sys/types.h>
    #include <sys/socket.h>
    #include <sys/un.h>

    int send_fd(int dest_fd, int subject_fd) {
        struct msghdr msg = {0};
        struct cmsghdr *cmsg;
        char buf[CMSG_SPACE(sizeof(subjectf_fd))];

        msg.msg_control = buf;
        msg.msg_controllen = sizeof buf;
        cmsg = CMSG_FIRSTHDR(&msg);
        cmsg->cmsg_level = SOL_SOCKET;
        cmsg->cmsg_type = SCM_RIGHTS;
        cmsg->cmsg_len = CMSG_LEN(sizeof(int));

        /* Initialize the payload: */
        fdptr = (int *) CMSG_DATA(cmsg);
        memcpy(fdptr, myfds, sizeof(int));

        /* Sum of the length of all control messages in the buffer: */
        msg.msg_controllen = cmsg->cmsg_len;

        return sendmsg(int sockfd, const struct msghdr *msg, int flags);
    }

    int recv_buf_or_fd(int src_fd, char *buf4k, int *subject_fd, int flags) {
        int res;
        struct msghdr msg = {0};
        struct iovec vec;
        struct cmsghdr *cmsg;
        char ctrl_buf[CMSG_SPACE(sizeof(int))];

        /* For the data that may arrive */
        vec.iov_base = buf4k;
        vec.iov_len = 4096;

        message.msg_control = ctrl_buf;
        message.msg_controllen = CMSG_SPACE(sizeof(int));
        message.msg_iov = &vec;
        message.msg_iovlen = 1;
        
        if((res = recvmsg(src_fd, &message, 0)) <= 0)
            return -errno;
        
        /* Iterate through header to find if there is a file descriptor */
        for(cmsg = CMSG_FIRSTHDR(&message); cmsg != NULL; cmsg = CMSG_NXTHDR(&message, cmsg))
        {
            if((cmsg->cmsg_level == SOL_SOCKET) && (cmsg->cmsg_type == SCM_RIGHTS) )
            {
                return *((int *) CMSG_DATA(control_message));
            }
        }

        
    }
""")

def sender():
    r = pipe[0]
    def a():
        i = 0
        while 1:
            i += 1
            r.put('msg {}'.format(i))
            gevent.sleep(1)
    gevent.spawn(a)

    def b():
        while 1:
            pair = os.pipe()
            
    gevent.spawn(b)

def receiver():
    w = pipe[1]
    while 1:
        print w.get()

pipe = gevent.socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)

gipc.start_process(receiver)

sender()