// P7 Distributed Computing — gRPC front-end for the control plane.
//
// Runs the production gRPC boundary alongside the stdlib HTTP reference
// server, in a separate goroutine. The service mirrors the HTTP API:
//   RegisterNode, ListNodes, SubmitTask, ClaimTask, CompleteTask.
package main

import (
	"context"
	"log"
	"net"

	pb "prometheus/internal/proto"
	"prometheus/internal/controlplane"
	"google.golang.org/grpc"
)

type grpcServer struct {
	pb.UnimplementedControlPlaneServer
	cp *controlplane.ControlPlane
}

func (s *grpcServer) RegisterNode(ctx context.Context, req *pb.RegisterNodeRequest) (*pb.RegisterNodeResponse, error) {
	s.cp.RegisterNode(req.GetId())
	return &pb.RegisterNodeResponse{Ok: true}, nil
}

func (s *grpcServer) ListNodes(ctx context.Context, req *pb.ListNodesRequest) (*pb.ListNodesResponse, error) {
	nodes := s.cp.ListNodes()
	out := make([]*pb.Node, 0, len(nodes))
	for _, n := range nodes {
		out = append(out, &pb.Node{
			Id:        n.ID,
			LastSeen:  n.LastSeen.Format("2006-01-02T15:04:05Z07:00"),
			Available: n.Available,
		})
	}
	return &pb.ListNodesResponse{Nodes: out}, nil
}

func (s *grpcServer) SubmitTask(ctx context.Context, req *pb.SubmitTaskRequest) (*pb.SubmitTaskResponse, error) {
	t := s.cp.SubmitTask(req.GetPayload())
	return &pb.SubmitTaskResponse{Task: toPBTask(t)}, nil
}

func (s *grpcServer) ClaimTask(ctx context.Context, req *pb.ClaimTaskRequest) (*pb.ClaimTaskResponse, error) {
	t := s.cp.ClaimTask(req.GetNode())
	if t == nil {
		return &pb.ClaimTaskResponse{}, nil
	}
	return &pb.ClaimTaskResponse{Task: toPBTask(t)}, nil
}

func (s *grpcServer) CompleteTask(ctx context.Context, req *pb.CompleteTaskRequest) (*pb.CompleteTaskResponse, error) {
	s.cp.CompleteTask(req.GetId())
	return &pb.CompleteTaskResponse{Ok: true}, nil
}

func toPBTask(t *controlplane.Task) *pb.Task {
	return &pb.Task{Id: t.ID, NodeId: t.NodeID, Status: t.Status, Payload: t.Payload}
}

func startGRPC(cp *controlplane.ControlPlane) {
	lis, err := net.Listen("tcp", ":8082")
	if err != nil {
		log.Printf("grpc listen: %v", err)
		return
	}
	srv := grpc.NewServer()
	pb.RegisterControlPlaneServer(srv, &grpcServer{cp: cp})
	go func() {
		log.Println("control plane gRPC listening on :8082")
		if err := srv.Serve(lis); err != nil {
			log.Printf("grpc serve: %v", err)
		}
	}()
}
